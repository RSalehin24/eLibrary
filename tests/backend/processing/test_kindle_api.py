from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import UserBook
from apps.delivery.serializers import recipient_outcomes
from apps.processing.job_models import BackgroundJob
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def kindle_reader(preparation_job, settings):
    settings.ACCOUNT_INVITE_FROM_EMAIL = "library@example.test"
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    user = preparation_job.requested_by
    user.is_staff = False
    user.kindle_emails = ["reader@kindle.com", "other@kindle.com"]
    user.save()
    UserBook.objects.create(user=user, book=preparation_job.book)
    client = APIClient()
    client.force_authenticate(user)
    return client, user, preparation_job


def request_fields(job):
    return {
        "operation_id": str(uuid4()),
        "expected_updated_at": job.asset.updated_at.isoformat(),
        "recipients": ["reader@kindle.com"],
    }


def book_path(job):
    return f"/api/v1/delivery/books/{job.book.slug}/kindle/"


def test_kindler_request_is_persisted_idempotent_and_returns_an_owner_status_url(
    kindle_reader, monkeypatch
):
    client, user, asset_job = kindle_reader

    def no_serving_network(**_):
        raise AssertionError("Reader requests must not open SMTP.")

    monkeypatch.setattr("apps.delivery.mail_transport.EmailBackend", no_serving_network)
    options = client.get(book_path(asset_job))
    assert options.status_code == 200 and options.data["configured"] is True
    assert options.data["recipients"] == user.kindle_emails
    fields = request_fields(asset_job)
    response = client.post(book_path(asset_job), fields, format="json")
    assert response.status_code == 202
    assert (
        response.data["status_url"]
        == f"/api/v1/delivery/operations/{response.data['operation_id']}/"
    )
    assert client.get(response.data["status_url"]).status_code == 200
    assert (
        client.get(f"/api/v1/manage/jobs/{response.data['operation_id']}/").status_code
        == 403
    )
    duplicate = client.post(book_path(asset_job), fields, format="json")
    assert duplicate.status_code == 202 and duplicate.data == response.data
    job = BackgroundJob.objects.get(pk=response.data["operation_id"])
    assert job.requested_by == user and job.dispatches.count() == 1


def test_kindler_permissions_are_independent_of_reading_and_metadata(kindle_reader):
    _, _user, asset_job = kindle_reader
    other = User.objects.create_user(
        email="kindle-scope@library.test", kindle_emails=["reader@kindle.com"]
    )
    client = APIClient()
    client.force_authenticate(other)
    PermissionGrant.objects.create(
        user=other, book=asset_job.book, scope=PermissionScope.READ_DURABLE
    )
    assert client.get(book_path(asset_job)).status_code == 403
    PermissionGrant.objects.create(
        user=other, book=asset_job.book, scope=PermissionScope.SEND_KINDLE
    )
    assert (
        client.post(
            book_path(asset_job), request_fields(asset_job), format="json"
        ).status_code
        == 202
    )
    assert APIClient().get(book_path(asset_job)).status_code == 403


@pytest.mark.parametrize(
    "recipients",
    [
        ["wrong@example.test"],
        ["not-configured@kindle.com"],
        [],
        ["reader@kindle.com"] * 11,
    ],
)
def test_recipients_must_be_explicit_bounded_and_in_the_current_profile(
    kindle_reader, recipients
):
    client, _, job = kindle_reader
    response = client.post(
        book_path(job), {**request_fields(job), "recipients": recipients}, format="json"
    )
    assert response.status_code == 400 and "recipients" in response.data["field_errors"]
    assert BackgroundJob.objects.count() == 1


def test_kindler_operations_are_private_after_permissions_change(kindle_reader):
    client, user, asset_job = kindle_reader
    response = client.post(
        book_path(asset_job), request_fields(asset_job), format="json"
    )
    url = response.data["status_url"]
    other = User.objects.create_user(email="other-kindler@library.test")
    foreign = APIClient()
    foreign.force_authenticate(other)
    assert foreign.get(url).status_code == 404
    assert foreign.get("/api/v1/me/kindle/").data["entries"] == []
    UserBook.objects.filter(user=user).update(user=other)
    assert client.get(url).status_code == 200
    detail = client.get(url)
    assert (
        detail["Cache-Control"] == "private, no-store"
        and detail["X-Robots-Tag"] == "noindex"
    )
    assert "input" not in detail.data and "asset" not in detail.data
    cancellation = client.post(
        url, {"expected_updated_at": detail.data["updated_at"]}, format="json"
    )
    assert cancellation.status_code == 202
    assert client.get(url).data["state"] == "cancelled"


def test_kindler_stale_asset_config_and_operation_revisions_conflict(
    kindle_reader, settings
):
    client, _, asset_job = kindle_reader
    fields = request_fields(asset_job)
    asset_job.asset.save()
    assert client.post(book_path(asset_job), fields, format="json").status_code == 409
    settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    assert client.get(book_path(asset_job)).data["configured"] is False
    assert (
        client.post(
            book_path(asset_job), request_fields(asset_job), format="json"
        ).status_code
        == 409
    )
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    response = client.post(
        book_path(asset_job), request_fields(asset_job), format="json"
    )
    detail = client.get(response.data["status_url"])
    assert (
        client.post(
            response.data["status_url"],
            {"expected_updated_at": detail.data["updated_at"]},
            format="json",
        ).status_code
        == 202
    )
    assert (
        client.post(
            response.data["status_url"],
            {"expected_updated_at": detail.data["updated_at"]},
            format="json",
        ).status_code
        == 409
    )


def test_kindler_collection_uses_owner_bound_cursors_and_bounded_queries(kindle_reader):
    client, user, asset_job = kindle_reader
    BackgroundJob.objects.bulk_create(
        [
            BackgroundJob(
                requested_by=user,
                book=asset_job.book,
                asset=asset_job.asset,
                kind="deliver_kindle",
                input={"recipients": ["reader@kindle.com"]},
                available_at=timezone.now(),
            )
            for _ in range(25)
        ]
    )
    with CaptureQueriesContext(connection) as small:
        first = client.get("/api/v1/me/kindle/?limit=1")
    with CaptureQueriesContext(connection) as large:
        page = client.get("/api/v1/me/kindle/?limit=24")
    assert len(small) == len(large) <= 2 and len(page.data["entries"]) == 24
    cursor = first.data["next_cursor"]
    assert (
        cursor
        and client.get(f"/api/v1/me/kindle/?limit=1&cursor={cursor}").data["entries"][
            0
        ]["id"]
        != first.data["entries"][0]["id"]
    )
    other = User.objects.create_user(email="kindler-cursor@library.test")
    client.force_authenticate(other)
    assert client.get(f"/api/v1/me/kindle/?cursor={cursor}").status_code == 400


def test_kindler_recipient_outcomes_separate_confirmed_unknown_and_unstarted():
    from types import SimpleNamespace

    job = SimpleNamespace(
        state="needs_attention",
        input={
            "recipients": [
                "accepted@kindle.com",
                "unknown@kindle.com",
                "waiting@kindle.com",
            ]
        },
        checkpoint={"accepted": [0], "sending_index": 1},
    )
    assert [entry["outcome"] for entry in recipient_outcomes(job)] == [
        "accepted",
        "uncertain",
        "pending",
    ]


def test_kindle_commands_enforce_real_session_csrf(kindle_reader):
    _, user, job = kindle_reader
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    fields = request_fields(job)
    assert client.post(book_path(job), fields, format="json").status_code == 403
    csrf = client.get("/api/v1/auth/session/").data["csrf_token"]
    assert (
        client.post(
            book_path(job), fields, format="json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 202
    )
