import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from django.test import Client
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PROFILE_URL = "/api/v1/auth/profile/"


@pytest.fixture
def account():
    user = User.objects.create_user(
        email="profile@library.test", password="Reader-Original-Password-2026"
    )
    client = APIClient()
    client.force_authenticate(user)
    return client, user


def revision(client):
    return client.get(PROFILE_URL).json()["updated_at"]


def test_profile_is_private_and_changes_only_allowed_fields(account):
    client, user = account
    response = client.get(PROFILE_URL)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert "password" not in response.json()
    assert APIClient().get(PROFILE_URL).status_code == 403
    changed = client.patch(
        PROFILE_URL,
        {
            "expected_updated_at": revision(client),
            "full_name": "পাঠকের নাম",
            "is_staff": True,
            "is_superuser": True,
        },
        format="json",
    )
    assert changed.status_code == 200
    user.refresh_from_db()
    assert user.full_name == "পাঠকের নাম" and not user.is_staff and not user.is_superuser


def test_stale_and_missing_profile_revisions_are_explicit(account):
    client, _ = account
    version = revision(client)
    assert (
        client.patch(PROFILE_URL, {"full_name": "নাম"}, format="json").status_code == 400
    )
    assert (
        client.patch(
            PROFILE_URL,
            {"expected_updated_at": version, "full_name": "প্রথম"},
            format="json",
        ).status_code
        == 200
    )
    stale = client.patch(
        PROFILE_URL,
        {"expected_updated_at": version, "full_name": "দ্বিতীয়"},
        format="json",
    )
    assert stale.status_code == 409 and stale.json()["code"] == "state_conflict"


@pytest.mark.parametrize("grant", ["owner", "book", "global"])
def test_kindle_addresses_work_for_ownership_and_scoped_permissions(account, grant):
    client, user = account
    book = Book.objects.create(title="কিন্ডলের বই")
    if grant == "owner":
        UserBook.objects.create(user=user, book=book)
    else:
        PermissionGrant.objects.create(
            user=user,
            book=book if grant == "book" else None,
            scope=PermissionScope.SEND_KINDLE,
        )
    assert client.get(PROFILE_URL).json()["can_configure_kindle"]
    changed = client.patch(
        PROFILE_URL,
        {
            "expected_updated_at": revision(client),
            "kindle_emails": ["READER@KINDLE.COM", "reader@kindle.com"],
        },
        format="json",
    )
    assert changed.status_code == 200
    assert changed.json()["kindle_emails"] == ["reader@kindle.com"]


def test_kindle_settings_require_permission_and_valid_domains(account):
    client, user = account
    values = {
        "expected_updated_at": revision(client),
        "kindle_emails": ["reader@kindle.com"],
    }
    assert client.patch(PROFILE_URL, values, format="json").status_code == 400
    PermissionGrant.objects.create(user=user, scope=PermissionScope.SEND_KINDLE)
    values["kindle_emails"] = ["reader@outside.test"]
    assert client.patch(PROFILE_URL, values, format="json").status_code == 400
    user.refresh_from_db()
    assert user.kindle_emails == []


@pytest.mark.parametrize(
    "fields",
    [
        {
            "current_password": "wrong",
            "new_password": "New-Reader-Password-2026",
            "confirm_new_password": "New-Reader-Password-2026",
        },
        {
            "current_password": "Reader-Original-Password-2026",
            "new_password": "short",
            "confirm_new_password": "short",
        },
        {
            "current_password": "Reader-Original-Password-2026",
            "new_password": "New-Reader-Password-2026",
            "confirm_new_password": "different",
        },
    ],
)
def test_password_changes_validate_current_password_and_confirmation(account, fields):
    client, user = account
    result = client.patch(
        PROFILE_URL, {"expected_updated_at": revision(client), **fields}, format="json"
    )
    assert result.status_code == 400 and result.json()["field_errors"]
    user.refresh_from_db()
    assert user.check_password("Reader-Original-Password-2026")


def test_password_change_retains_current_session_and_revokes_old_sessions(account):
    _, user = account
    current, other = Client(enforce_csrf_checks=True), Client()
    current.force_login(user)
    other.force_login(user)
    token = current.get("/api/v1/auth/session/").json()["csrf_token"]
    values = {
        "expected_updated_at": revision(current),
        "current_password": "Reader-Original-Password-2026",
        "new_password": "New-Reader-Password-2026",
        "confirm_new_password": "New-Reader-Password-2026",
    }
    assert (
        current.patch(PROFILE_URL, values, content_type="application/json").status_code
        == 403
    )
    assert (
        current.patch(
            PROFILE_URL, values, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )
    assert current.get(PROFILE_URL).status_code == 200
    assert other.get(PROFILE_URL).status_code == 403
