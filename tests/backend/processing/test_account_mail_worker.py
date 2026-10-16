from contextlib import nullcontext
from datetime import timedelta
from email.parser import BytesParser
from email.policy import default
from smtplib import SMTPDataError, SMTPServerDisconnected
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.link_mail.requests import (
    request_invitation,
    request_invitation_resend,
    request_password_reset,
)
from apps.accounts.models import User
from apps.accounts.serializers.support import password_link_token_generator
from apps.processing.job_models import BackgroundJob, JobAttempt
from apps.processing.jobs.attempts import checkpoint_attempt, claim_attempt
from apps.processing.jobs.controls import request_stop
from apps.processing.jobs.dispatches import claim_dispatches
from apps.processing.jobs.recovery import recover_stale_attempts
from apps.processing.jobs.worker import run_background_job
from django.db import DatabaseError, IntegrityError, transaction
from django.test import Client
from django.utils import timezone
from smtp_fixture import local_smtp

from tests.backend.auth.account_mail_fixtures import invite_values

pytestmark = pytest.mark.django_db


@pytest.fixture
def account_job(settings):
    settings.FRONTEND_BASE_URL = "https://library.example.test"
    settings.ACCOUNT_INVITE_FROM_EMAIL = "library@example.test"
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    actor = User.objects.create_user(email="mail-manager@library.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.ACCESS_MANAGE)
    return request_invitation(actor, invite_values())


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


def test_account_mail_acceptance_is_durable_and_duplicate_delivery_does_not_send(
    account_job, smtp_connection
):
    execute(account_job)
    assert account_job.state == "succeeded" and "accepted_at" in account_job.checkpoint
    message = smtp_connection.send_messages.call_args.args[0][0]
    link = next(
        line for line in message.body.splitlines() if line.startswith("https://")
    )
    url = urlsplit(link)
    assert url.path == "/create-password/" and not url.query
    token = parse_qs(url.fragment)["token"][0]
    assert password_link_token_generator.check_token(account_job.account, token)
    assert not message.attachments
    execute(account_job)
    assert smtp_connection.send_messages.call_count == 1


@pytest.mark.parametrize(
    "outcome, state",
    [
        (SMTPDataError(451, b"fixture"), "retry_wait"),
        (SMTPDataError(550, b"fixture"), "failed"),
        (SMTPServerDisconnected("fixture"), "needs_attention"),
    ],
)
def test_known_rejections_and_unknown_acceptance_are_classified(
    account_job, smtp_connection, outcome, state
):
    smtp_connection.send_messages.side_effect = outcome
    execute(account_job)
    assert account_job.state == state and smtp_connection.send_messages.call_count == 1
    assert account_job.dispatches.count() == (2 if state == "retry_wait" else 1)


def test_database_failure_after_submission_never_retries(
    account_job, smtp_connection, monkeypatch
):
    def fail_record(_):
        raise DatabaseError("synthetic")

    monkeypatch.setattr("apps.accounts.link_mail.worker.record_acceptance", fail_record)
    execute(account_job)
    assert (
        account_job.state == "needs_attention"
        and account_job.error_code == "mail_acceptance_unknown"
    )
    execute(account_job)
    assert smtp_connection.send_messages.call_count == 1


def test_superseded_invitation_fails_before_connecting(account_job, smtp_connection):
    request_invitation_resend(
        account_job.requested_by,
        account_job.account_id,
        {
            "operation_id": "946c1ea1-2e3a-47bf-b243-c269f3606687",
            "expected_updated_at": account_job.account.updated_at.isoformat(),
        },
    )
    execute(account_job)
    assert (
        account_job.state == "failed"
        and account_job.error_code == "account_link_superseded"
    )
    assert smtp_connection.open.call_count == 0


def test_revoked_manager_authority_prevents_invitation_delivery(
    account_job, smtp_connection
):
    PermissionGrant.objects.filter(user=account_job.requested_by).update(
        is_active=False
    )
    execute(account_job)
    assert (
        account_job.state == "failed" and account_job.error_code == "permission_revoked"
    )
    assert smtp_connection.open.call_count == 0


def test_cancellation_while_connecting_stops_before_submission(
    account_job, smtp_connection
):
    smtp_connection.open.side_effect = lambda: request_stop(account_job.pk, "cancel")
    execute(account_job)
    assert (
        account_job.state == "cancelled"
        and smtp_connection.send_messages.call_count == 0
    )


def test_late_cancellation_preserves_confirmed_acceptance(account_job, smtp_connection):
    smtp_connection.send_messages.side_effect = lambda _: (
        request_stop(account_job.pk, "cancel"),
        1,
    )[1]
    execute(account_job)
    assert account_job.state == "succeeded" and "accepted_at" in account_job.checkpoint


def test_stale_sending_attempt_requires_review_without_new_dispatch(account_job):
    ownership = claim_attempt(account_job.dispatches.get().pk)
    checkpoint_attempt(ownership, {}, "sending")
    old = timezone.now() - timedelta(minutes=10)
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(heartbeat_at=old)
    assert recover_stale_attempts(timezone.now() - timedelta(minutes=3)) == 1
    account_job.refresh_from_db()
    assert (
        account_job.state == "needs_attention" and account_job.dispatches.count() == 1
    )


def test_account_mail_uses_delivery_queue_and_domain_constraint(account_job):
    assert claim_dispatches()[0].queue == "delivery"
    with pytest.raises(IntegrityError), transaction.atomic():
        BackgroundJob.objects.create(kind="account_mail", available_at=timezone.now())


@pytest.mark.parametrize(
    "origin",
    [
        "http://library.example.test",
        "https://reader:password@library.test",
        "https://library.test/subpath",
        "https://library.test/#fragment",
        "https://library..test",
        "https://library.test:0",
    ],
)
def test_unsafe_frontend_origins_fail_before_mail_connection(
    account_job, smtp_connection, settings, origin
):
    settings.FRONTEND_BASE_URL = origin
    execute(account_job)
    assert (
        account_job.state == "failed"
        and account_job.error_code == "mail_frontend_origin_invalid"
    )
    assert smtp_connection.open.call_count == 0


@pytest.mark.parametrize(
    "outcome, state", [("accept", "succeeded"), ("disconnect", "needs_attention")]
)
def test_real_loopback_smtp_sends_a_fragment_link_and_preserves_acceptance(
    account_job, settings, outcome, state
):
    with local_smtp(outcome) as server:
        settings.EMAIL_PORT = server.server_address[1]
        settings.EMAIL_USE_TLS = settings.EMAIL_USE_SSL = False
        settings.EMAIL_HOST_USER = settings.EMAIL_HOST_PASSWORD = ""
        execute(account_job)
        assert account_job.state == state and len(server.messages) == 1
        message = BytesParser(policy=default).parsebytes(server.messages[0])
        assert "/create-password/#uid=" in message.get_content()
        execute(account_job)
        assert len(server.messages) == 1


def test_delivered_invitation_link_completes_password_and_required_totp_setup_gate(
    account_job, smtp_connection
):
    execute(account_job)
    body = smtp_connection.send_messages.call_args.args[0][0].body
    url = urlsplit(
        next(line for line in body.splitlines() if line.startswith("https://"))
    )
    ticket = {key: value[0] for key, value in parse_qs(url.fragment).items()}
    client = Client(enforce_csrf_checks=True)
    csrf = client.get("/api/v1/auth/session/").json()["csrf_token"]
    inspected = client.post(
        "/api/v1/auth/password-links/inspect/",
        ticket,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert inspected.json() == {"purpose": "setup", "totp_setup_required": True}
    values = {
        **ticket,
        "new_password": "  zR#482mQ!85-safe-password  ",
        "confirm_new_password": "  zR#482mQ!85-safe-password  ",
    }
    confirmed = client.post(
        "/api/v1/auth/password-links/confirm/",
        values,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert (
        confirmed.status_code == 200 and confirmed.json()["next_step"] == "totp_setup"
    )
    assert client.get("/api/v1/me/books/").json()["code"] == "otp_setup_required"
    target = account_job.account
    target.refresh_from_db()
    assert target.check_password(values["new_password"])
    assert not password_link_token_generator.check_token(target, ticket["token"])


def test_reset_mail_uses_confirmation_path_and_is_not_an_administrator_operation(
    settings, smtp_connection
):
    settings.FRONTEND_BASE_URL = "https://library.example.test"
    settings.ACCOUNT_INVITE_FROM_EMAIL = "library@example.test"
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    target = User.objects.create_user(
        email="reset-worker@library.test", password="previous-password"
    )
    request_password_reset(target.email)
    job = BackgroundJob.objects.get()
    execute(job)
    assert job.state == "succeeded" and job.requested_by is None
    assert (
        "/reset-password/confirm/#uid="
        in smtp_connection.send_messages.call_args.args[0][0].body
    )
