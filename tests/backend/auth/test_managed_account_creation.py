from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.processing.job_models import BackgroundJob
from django.test import Client

from .managed_access_fixtures import USERS

pytestmark = pytest.mark.django_db


def creation_values():
    return {
        "operation_id": str(uuid4()),
        "email": "Direct-Reader@Library.test",
        "full_name": "নতুন পাঠক",
        "password": "  reader-password  ",
        "confirm_password": "  reader-password  ",
        "totp_required": False,
    }


@pytest.fixture
def superadministrator(client):
    actor = User.objects.create_superuser(
        email="super@library.test", password="administrator-password"
    )
    client.force_login(actor)
    return actor


def create(client, values):
    return client.post(USERS, values, content_type="application/json")


def test_direct_creation_preserves_password_spaces_and_never_sends_mail(
    client, superadministrator, mailoutbox
):
    values = creation_values()
    response = create(client, values)
    assert response.status_code == 201
    target = User.objects.get(pk=response.json()["id"])
    assert target.email == values["email"].lower()
    assert target.check_password(values["password"])
    assert not target.check_password(values["password"].strip())
    assert target.is_active and not target.email_setup_pending
    assert not target.is_superuser and not target.is_staff
    assert not PermissionGrant.objects.filter(user=target).exists()
    assert not BackgroundJob.objects.exists() and not mailoutbox
    assert "password" not in response.json()
    assert response["Cache-Control"] == "private, no-store"
    audit = AuditLog.objects.get(pk=values["operation_id"])
    assert audit.actor == superadministrator and audit.target_id == str(target.pk)
    assert audit.payload == {} and audit.request_id == ""


def test_direct_creation_is_idempotent_and_changed_password_never_resets_account(
    client, superadministrator
):
    values = creation_values()
    first, second = create(client, values), create(client, values)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json() and AuditLog.objects.count() == 1
    changed = {
        **values,
        "password": "changed-password",
        "confirm_password": "changed-password",
    }
    assert create(client, changed).status_code == 409
    target = User.objects.get(pk=first.json()["id"])
    target.set_password("reader-changed-password")
    target.save()
    assert create(client, values).status_code == 409
    target.refresh_from_db()
    assert target.check_password("reader-changed-password")


@pytest.mark.parametrize("role", ["access_manager", "staff", "full_control", "reader"])
def test_initial_password_requires_superadministrator(client, role):
    actor = User.objects.create_user(
        email="ordinary@library.test", is_staff=role == "staff"
    )
    scopes = {
        "access_manager": PermissionScope.ACCESS_MANAGE,
        "full_control": PermissionScope.ADMIN_FULL_CONTROL,
    }
    if role in scopes:
        PermissionGrant.objects.create(user=actor, scope=scopes[role])
    client.force_login(actor)
    assert create(client, creation_values()).status_code == 403
    assert User.objects.count() == 1 and not AuditLog.objects.exists()


@pytest.mark.parametrize(
    "changes,field",
    [
        ({"password": "short", "confirm_password": "short"}, "password"),
        ({"confirm_password": "different-password"}, "confirm_password"),
        ({"is_staff": True}, "is_staff"),
        ({"is_superuser": True}, "is_superuser"),
        ({"global_scopes": ["admin:full_control"]}, "global_scopes"),
        ({"email": "invalid"}, "email"),
    ],
)
def test_invalid_creation_is_atomic(client, superadministrator, changes, field):
    response = create(client, {**creation_values(), **changes})
    assert response.status_code == 400 and field in response.json()["field_errors"]
    assert User.objects.count() == 1 and not AuditLog.objects.exists()


@pytest.mark.parametrize(
    "password", ["password1234", "1234567890123456", "Direct-Reader@Library.test"]
)
def test_initial_password_applies_existing_strength_policy(
    client, superadministrator, password
):
    values = {**creation_values(), "password": password, "confirm_password": password}
    response = create(client, values)
    assert response.status_code == 400 and "password" in response.json()["field_errors"]
    assert User.objects.count() == 1 and not AuditLog.objects.exists()


def test_case_insensitive_duplicate_and_foreign_operation_are_rejected(
    client, superadministrator
):
    values = creation_values()
    assert create(client, values).status_code == 201
    duplicate = {
        **values,
        "operation_id": str(uuid4()),
        "email": values["email"].upper(),
    }
    assert create(client, duplicate).status_code == 400
    other = User.objects.create_superuser(
        email="other@library.test", password="administrator-password"
    )
    client.force_login(other)
    assert create(client, values).status_code == 409
    assert AuditLog.objects.count() == 1


def test_direct_creation_requires_real_csrf_and_current_authority(
    client, superadministrator
):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(superadministrator)
    assert create(strict, creation_values()).status_code == 403
    superadministrator.is_superuser = False
    superadministrator.save()
    assert create(client, creation_values()).status_code == 403
    assert User.objects.count() == 1


def test_required_totp_is_kept_for_initial_password_accounts(
    client, superadministrator
):
    response = create(client, {**creation_values(), "totp_required": True})
    assert response.status_code == 201
    target = User.objects.get(pk=response.json()["id"])
    assert target.requires_totp_setup and not target.email_setup_pending


def test_direct_account_can_start_disabled_without_losing_its_password(
    client, superadministrator
):
    values = {**creation_values(), "is_active": False}
    response = create(client, values)
    assert response.status_code == 201 and response.json()["is_active"] is False
    assert create(client, values).json() == response.json()
    assert create(client, {**values, "is_active": True}).status_code == 409
    target = User.objects.get(pk=response.json()["id"])
    assert not target.is_active and target.check_password(values["password"])
    assert not Client().login(username=target.email, password=values["password"])
