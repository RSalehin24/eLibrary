from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.accounts.serializers.support import password_link_token_generator
from apps.processing.job_models import BackgroundJob
from django.core.cache import cache
from django.test import Client

INVITES = "/api/v1/manage/invitations/"
RESET = "/api/v1/auth/password-reset/"
pytestmark = pytest.mark.django_db

from .account_mail_fixtures import invite_values


@pytest.fixture(autouse=True)
def reset_throttle():
    cache.delete("throttle_password_reset_127.0.0.1")
    yield
    cache.delete("throttle_password_reset_127.0.0.1")


def post(client, path, values):
    return client.post(path, values, content_type="application/json")


def test_invitation_creates_unprivileged_account_and_outbox_without_sending_mail(
    client, accounts, mailoutbox
):
    response = post(client, INVITES, invite_values())
    assert response.status_code == 202
    job = BackgroundJob.objects.get(pk=response.json()["operation_id"])
    target = job.account
    assert job.book_id is None and job.asset_id is None and job.dispatches.count() == 1
    assert target.email == "new-reader@library.test" and target.email_setup_pending
    assert target.totp_required and not target.has_usable_password()
    assert (
        not target.is_staff
        and not target.is_superuser
        and not PermissionGrant.objects.filter(user=target).exists()
    )
    assert len(mailoutbox) == 0
    status = client.get(response.json()["status_url"])
    assert status.status_code == 200 and status.json()["account_id"] == target.pk
    assert "input" not in status.json() and "email" not in status.json()
    assert (
        status["Cache-Control"] == "private, no-store"
        and status["X-Robots-Tag"] == "noindex"
    )


def test_repeating_the_same_invitation_is_idempotent(client, accounts):
    values = invite_values()
    first, second = post(client, INVITES, values), post(client, INVITES, values)
    assert (
        first.status_code == second.status_code == 202 and first.json() == second.json()
    )
    assert BackgroundJob.objects.count() == 1
    changed = {**values, "full_name": "অন্য নাম"}
    assert post(client, INVITES, changed).status_code == 409


@pytest.mark.parametrize(
    "field", ["is_staff", "is_superuser", "global_scopes", "password"]
)
def test_invitation_cannot_assign_privileges_or_passwords(client, accounts, field):
    assert post(client, INVITES, {**invite_values(), field: True}).status_code == 400
    assert not BackgroundJob.objects.exists()


def test_existing_case_insensitive_email_is_rejected_without_a_second_account(
    client, accounts
):
    values = invite_values()
    User.objects.create_user(email=values["email"].upper())
    response = post(client, INVITES, values)
    assert response.status_code == 400 and "email" in response.json()["field_errors"]
    assert not BackgroundJob.objects.exists()


@pytest.mark.parametrize(
    "scope", [None, PermissionScope.PROCESSING_MANAGE, PermissionScope.METADATA_EDIT]
)
def test_invitation_requires_global_access_management(client, scope):
    actor = User.objects.create_user(email="denied-invite@library.test")
    if scope:
        PermissionGrant.objects.create(user=actor, scope=scope)
    client.force_login(actor)
    assert post(client, INVITES, invite_values()).status_code == 403
    assert not BackgroundJob.objects.exists()


def test_processing_managers_cannot_list_read_or_control_account_mail(client, accounts):
    response = post(client, INVITES, invite_values())
    identifier = response.json()["operation_id"]
    processor = User.objects.create_user(email="private-mail@library.test")
    PermissionGrant.objects.create(
        user=processor, scope=PermissionScope.PROCESSING_MANAGE
    )
    client.force_login(processor)
    assert client.get("/api/v1/manage/jobs/").json()["entries"] == []
    url = f"/api/v1/manage/jobs/{identifier}/"
    assert client.get(url).status_code == 404
    job = BackgroundJob.objects.get(pk=identifier)
    values = {"action": "cancel", "expected_updated_at": job.updated_at.isoformat()}
    assert post(client, url, values).status_code == 404
    assert client.get(response.json()["status_url"]).status_code == 403


def test_resend_uses_revision_supersedes_links_and_is_idempotent(client, accounts):
    response = post(client, INVITES, invite_values())
    first = BackgroundJob.objects.get(pk=response.json()["operation_id"])
    target = first.account
    token = password_link_token_generator.make_token(target)
    values = {
        "operation_id": str(uuid4()),
        "expected_updated_at": target.updated_at.isoformat(),
    }
    url = f"/api/v1/manage/users/{target.pk}/invitation/"
    second = post(client, url, values)
    assert (
        second.status_code == 202 and post(client, url, values).json() == second.json()
    )
    target.refresh_from_db()
    assert (
        target.password_setup_nonce == 1
        and not password_link_token_generator.check_token(target, token)
    )
    assert (
        post(client, url, {**values, "operation_id": str(uuid4())}).status_code == 409
    )
    listing = client.get(f"/api/v1/manage/users/{target.pk}/mail/").json()
    assert listing["pagination"]["total_count"] == 2


def test_resend_rejects_completed_accounts_and_protected_targets(client, accounts):
    actor, target = accounts
    values = {
        "operation_id": str(uuid4()),
        "expected_updated_at": target.updated_at.isoformat(),
    }
    assert (
        post(
            client, f"/api/v1/manage/users/{target.pk}/invitation/", values
        ).status_code
        == 409
    )
    assert (
        post(client, f"/api/v1/manage/users/{actor.pk}/invitation/", values).status_code
        == 403
    )


def test_reset_has_identical_public_response_for_eligible_ineligible_and_missing_accounts(
    client,
):
    active = User.objects.create_user(
        email="reset-mail@library.test", password="existing-password"
    )
    disabled = User.objects.create_user(
        email="disabled-mail@library.test",
        password="existing-password",
        is_active=False,
    )
    pending = User.objects.create_user(
        email="pending-mail@library.test", email_setup_pending=True
    )
    responses = [
        post(client, RESET, {"email": email})
        for email in [
            active.email,
            disabled.email,
            pending.email,
            "unknown@library.test",
        ]
    ]
    assert all(response.status_code == 202 for response in responses)
    assert all(response.json() == responses[0].json() for response in responses)
    job = BackgroundJob.objects.get()
    assert (
        job.account == active
        and job.requested_by is None
        and job.dispatches.count() == 1
    )
    assert "operation_id" not in responses[0].json()


def test_reset_cooldown_keeps_one_job_and_does_not_keep_invalidating_links(client):
    target = User.objects.create_user(
        email="cooldown-mail@library.test", password="existing-password"
    )
    values = {"email": target.email}
    assert post(client, RESET, values).status_code == 202
    target.refresh_from_db()
    token = password_link_token_generator.make_token(target)
    assert post(client, RESET, values).status_code == 202
    target.refresh_from_db()
    assert target.password_setup_nonce == 1 and BackgroundJob.objects.count() == 1
    assert password_link_token_generator.check_token(target, token)


def test_reset_enforces_real_csrf_and_existing_five_per_hour_limit():
    client = Client(enforce_csrf_checks=True)
    values = {"email": "unknown@library.test"}
    assert post(client, RESET, values).status_code == 403
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    for _ in range(5):
        assert (
            client.post(
                RESET, values, content_type="application/json", HTTP_X_CSRFTOKEN=token
            ).status_code
            == 202
        )
    response = client.post(
        RESET, values, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 429 and "Retry-After" in response


def test_invitation_commands_enforce_real_csrf_and_reset_operations_are_not_exposed(
    accounts,
):
    from apps.accounts.link_mail.requests import request_password_reset

    actor, _ = accounts
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    values = invite_values()
    assert post(client, INVITES, values).status_code == 403
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    response = client.post(
        INVITES, values, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 202
    assert (
        client.post(
            response.json()["status_url"],
            {"action": "cancel"},
            content_type="application/json",
        ).status_code
        == 403
    )
    reset_user = User.objects.create_user(
        email="private-reset@library.test", password="previous-password"
    )
    request_password_reset(reset_user.email)
    job = BackgroundJob.objects.get(account=reset_user)
    assert client.get(f"/api/v1/manage/mail/{job.pk}/").status_code == 404
    assert (
        client.get(f"/api/v1/manage/users/{reset_user.pk}/mail/").json()["entries"]
        == []
    )


def test_reset_rejects_signed_in_requests_and_unknown_fields(client, accounts):
    assert post(client, RESET, {"email": "unknown@library.test"}).status_code == 400
    client.logout()
    assert (
        post(
            client, RESET, {"email": "unknown@library.test", "token": "extra"}
        ).status_code
        == 400
    )
