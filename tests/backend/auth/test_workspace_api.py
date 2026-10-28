from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    Category,
    Contributor,
)
from django.utils import timezone

pytestmark = pytest.mark.django_db
SESSION_URL = "/api/v1/auth/session/"
MANAGED_BOOKS_URL = "/api/v1/manage/books/"


def test_anonymous_session_has_reader_workspace_and_csrf_cookie(client):
    response = client.get(SESSION_URL)
    payload = response.json()
    assert payload["authenticated"] is False
    assert payload["user"] is None
    assert payload["workspaces"] == {
        "reader": True,
        "manage": False,
        "management_sections": [],
        "can_create_books": False,
        "can_edit_books": False,
    }
    assert payload["csrf_token"]
    assert "csrftoken" in response.cookies
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Robots-Tag"] == "noindex"


def test_reader_has_no_management_navigation_or_book_listing(client):
    user = User.objects.create_user(email="reader@example.com")
    client.force_login(user)
    assert client.get(SESSION_URL).json()["workspaces"]["management_sections"] == []
    response = client.get(MANAGED_BOOKS_URL)
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_processing_grant_does_not_allow_metadata_or_user_management(client):
    user = User.objects.create_user(email="processing@example.com")
    PermissionGrant.objects.create(user=user, scope=PermissionScope.PROCESSING_MANAGE)
    client.force_login(user)
    assert client.get(SESSION_URL).json()["workspaces"]["management_sections"] == [
        "overview",
        "sources",
        "jobs",
        "automations",
    ]
    assert client.get(MANAGED_BOOKS_URL).status_code == 403


@pytest.mark.parametrize(
    "fields", [{"is_active": False}, {"expires_at": timezone.now() - timedelta(days=1)}]
)
def test_inactive_or_expired_grants_do_not_enable_management(client, fields):
    user = User.objects.create_user(email="expired@example.com")
    PermissionGrant.objects.create(
        user=user, scope=PermissionScope.ACCESS_MANAGE, **fields
    )
    client.force_login(user)
    assert client.get(SESSION_URL).json()["workspaces"]["manage"] is False


def test_scoped_metadata_grant_lists_only_the_matching_book(client):
    user = User.objects.create_user(email="scoped@example.com")
    allowed = Book.objects.create(title="অনুমোদিত খসড়া")
    Book.objects.create(title="অন্যের খসড়া")
    PermissionGrant.objects.create(
        user=user, scope=PermissionScope.METADATA_EDIT, book=allowed
    )
    client.force_login(user)
    assert client.get(SESSION_URL).json()["workspaces"]["management_sections"] == [
        "overview",
        "books",
    ]
    response = client.get(MANAGED_BOOKS_URL)
    assert [entry["id"] for entry in response.json()["entries"]] == [str(allowed.id)]
    assert response.json()["pagination"] == {"page": 1, "limit": 50, "total_count": 1}


def test_category_and_author_scopes_preserve_existing_permission_rules(client):
    user = User.objects.create_user(email="relationships@example.com")
    author = Contributor.objects.create(name="একজন লেখক")
    category = Category.objects.create(name="অনুমোদিত বিভাগ")
    by_author = Book.objects.create(title="লেখকের বই")
    translated = Book.objects.create(title="অনুবাদ করা বই")
    categorized = Book.objects.create(title="বিভাগের বই")
    BookContributor.objects.create(book=by_author, contributor=author, role="author")
    BookContributor.objects.create(
        book=translated, contributor=author, role="translator"
    )
    BookCategory.objects.create(book=categorized, category=category)
    PermissionGrant.objects.create(
        user=user, scope=PermissionScope.METADATA_EDIT, contributor=author
    )
    PermissionGrant.objects.create(
        user=user, scope=PermissionScope.METADATA_EDIT, category=category
    )
    client.force_login(user)
    entries = client.get(MANAGED_BOOKS_URL).json()["entries"]
    assert {entry["id"] for entry in entries} == {
        str(by_author.id),
        str(categorized.id),
    }


@pytest.mark.parametrize("fields", [{"is_staff": True}, {"is_superuser": True}])
def test_administrators_can_switch_workspaces(client, fields):
    user = User.objects.create_user(email="admin@example.com", **fields)
    client.force_login(user)
    assert client.get(SESSION_URL).json()["workspaces"]["management_sections"] == [
        "overview",
        "sources",
        "books",
        "jobs",
        "automations",
        "users-access",
    ]


def test_admin_pagination_is_required_and_bounded(client):
    user = User.objects.create_user(email="metadata@example.com")
    PermissionGrant.objects.create(user=user, scope=PermissionScope.METADATA_EDIT)
    for index in range(51):
        Book.objects.create(title=f"খসড়া বই {index}")
    client.force_login(user)
    response = client.get(MANAGED_BOOKS_URL)
    assert len(response.json()["entries"]) == 50
    assert response.json()["pagination"] == {"page": 1, "limit": 50, "total_count": 51}
    response = client.get(MANAGED_BOOKS_URL, {"page": 2})
    assert len(response.json()["entries"]) == 1
    assert client.get(MANAGED_BOOKS_URL, {"limit": 101}).status_code == 400
    assert client.get(MANAGED_BOOKS_URL, {"page": 0}).status_code == 400


def test_versioned_session_allows_totp_setup_but_protects_management(client):
    user = User.objects.create_user(email="totp@example.com", totp_required=True)
    PermissionGrant.objects.create(user=user, scope=PermissionScope.METADATA_EDIT)
    client.force_login(user)
    response = client.get(SESSION_URL)
    assert response.status_code == 200
    assert response.json()["user"]["totp_setup_required"] is True
    assert client.get(MANAGED_BOOKS_URL).json()["code"] == "otp_setup_required"
