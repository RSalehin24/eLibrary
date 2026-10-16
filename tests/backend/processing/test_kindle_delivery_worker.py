from contextlib import nullcontext
from smtplib import SMTPDataError, SMTPServerDisconnected
from unittest.mock import Mock

import pytest
from apps.catalog.models import UserBookKindleSend
from apps.processing.jobs.controls import request_stop
from apps.processing.jobs.worker import run_background_job
from django.db import DatabaseError
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def smtp_connection(monkeypatch):
    connection = Mock()
    connection.send_messages.return_value = 1
    monkeypatch.setattr(
        "apps.delivery.mail_transport.EmailBackend", lambda **_: connection
    )
    return connection


def execute(job):
    run_background_job(
        job.dispatches.get(generation=job.generation).pk, lambda _: nullcontext()
    )
    job.refresh_from_db()


def sent_recipients(connection):
    return [call.args[0][0].to[0] for call in connection.send_messages.call_args_list]


def test_confirmed_recipients_are_recorded_and_duplicate_worker_delivery_does_not_resend(
    kindle_job, smtp_connection
):
    execute(kindle_job)
    assert kindle_job.state == "succeeded" and kindle_job.checkpoint["accepted"] == [
        0,
        1,
    ]
    assert sent_recipients(smtp_connection) == kindle_job.input["recipients"]
    assert (
        UserBookKindleSend.objects.filter(
            user=kindle_job.requested_by, book=kindle_job.book
        ).count()
        == 1
    )
    execute(kindle_job)
    assert smtp_connection.send_messages.call_count == 2


def test_known_rejection_retries_only_the_unaccepted_recipient(
    kindle_job, smtp_connection
):
    smtp_connection.send_messages.side_effect = [1, SMTPDataError(451, b"synthetic"), 1]
    execute(kindle_job)
    assert kindle_job.state == "retry_wait" and kindle_job.checkpoint["accepted"] == [0]
    kindle_job.available_at = timezone.now()
    kindle_job.save(update_fields=["available_at"])
    execute(kindle_job)
    assert kindle_job.state == "succeeded" and kindle_job.checkpoint["accepted"] == [
        0,
        1,
    ]
    assert sent_recipients(smtp_connection) == [
        "reader@kindle.com",
        "other@kindle.com",
        "other@kindle.com",
    ]


def test_unknown_smtp_acceptance_requires_review_without_retry(
    kindle_job, smtp_connection
):
    smtp_connection.send_messages.side_effect = SMTPServerDisconnected(
        "synthetic interrupted acceptance"
    )
    execute(kindle_job)
    assert (
        kindle_job.state == "needs_attention"
        and kindle_job.error_code == "mail_acceptance_unknown"
    )
    assert kindle_job.checkpoint["sending_index"] == 0
    assert (
        kindle_job.dispatches.count() == 1 and not UserBookKindleSend.objects.exists()
    )
    execute(kindle_job)
    assert smtp_connection.send_messages.call_count == 1


def test_database_failure_after_smtp_acceptance_is_uncertain_and_cannot_resend(
    kindle_job, smtp_connection, monkeypatch
):
    def failed_record(*args, **kwargs):
        raise DatabaseError("synthetic acceptance persistence interruption")

    monkeypatch.setattr(UserBookKindleSend.objects, "update_or_create", failed_record)
    execute(kindle_job)
    assert (
        kindle_job.state == "needs_attention"
        and kindle_job.checkpoint.get("accepted", []) == []
    )
    assert kindle_job.checkpoint["sending_index"] == 0
    assert kindle_job.dispatches.count() == 1
    execute(kindle_job)
    assert smtp_connection.send_messages.call_count == 1


@pytest.mark.parametrize("change", ["permission", "recipient"])
def test_permission_and_address_changes_prevent_the_next_submission(
    kindle_job, smtp_connection, change
):
    def accept_and_revoke(_):
        actor = kindle_job.requested_by
        if change == "permission":
            actor.is_staff = False
        else:
            actor.kindle_emails = ["reader@kindle.com"]
        actor.save()
        return 1

    smtp_connection.send_messages.side_effect = accept_and_revoke
    execute(kindle_job)
    assert kindle_job.state == "failed" and kindle_job.checkpoint["accepted"] == [0]
    assert smtp_connection.send_messages.call_count == 1
    assert kindle_job.error_code in {"permission_revoked", "recipient_removed"}


def test_cancellation_after_a_submission_keeps_the_confirmed_recipient(
    kindle_job, smtp_connection
):
    def accept_and_cancel(_):
        request_stop(kindle_job.pk, "cancel")
        return 1

    smtp_connection.send_messages.side_effect = accept_and_cancel
    execute(kindle_job)
    assert kindle_job.state == "cancelled" and kindle_job.checkpoint["accepted"] == [0]
    assert smtp_connection.send_messages.call_count == 1
    assert UserBookKindleSend.objects.count() == 1


def test_a_late_cancellation_does_not_hide_a_fully_completed_delivery(
    kindle_job, smtp_connection
):
    def accept_and_cancel_last(_):
        if smtp_connection.send_messages.call_count == 2:
            request_stop(kindle_job.pk, "cancel")
        return 1

    smtp_connection.send_messages.side_effect = accept_and_cancel_last
    execute(kindle_job)
    assert kindle_job.state == "succeeded" and kindle_job.checkpoint["accepted"] == [
        0,
        1,
    ]


def test_attachment_size_limits_fail_before_mail_submission(
    kindle_job, smtp_connection, settings
):
    settings.KINDLE_MAX_ATTACHMENT_BYTES = 1
    execute(kindle_job)
    assert (
        kindle_job.state == "failed" and kindle_job.error_code == "attachment_too_large"
    )
    assert (
        smtp_connection.open.call_count == smtp_connection.send_messages.call_count == 0
    )


def test_replaced_assets_are_rejected_before_mail_submission(
    kindle_job, smtp_connection
):
    kindle_job.asset.save()
    execute(kindle_job)
    assert kindle_job.state == "failed" and kindle_job.error_code == "asset_changed"
    assert (
        smtp_connection.open.call_count == smtp_connection.send_messages.call_count == 0
    )
