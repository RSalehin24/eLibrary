from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, BookContributor, Category, Contributor, UserBook
from apps.common.models import AuditLog
from django.test import Client
from django.utils import timezone

from .managed_access_fixtures import REFERENCES, USERS, account_url, grant_request

pytestmark = pytest.mark.django_db


def test_access_manager_lists_private_account_metadata_with_bounded_queries(
    client, accounts, django_assert_max_num_queries
):
    for index in range(52):
        User.objects.create_user(email=f"account-{index}@library.test")
    with django_assert_max_num_queries(5):
        response = client.get(USERS)
    assert response.status_code == 200
    assert len(response.json()["entries"]) == 50
    assert response.json()["pagination"] == {"page": 1, "limit": 50, "total_count": 54}
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Robots-Tag"] == "noindex"
    entry = client.get(USERS, {"q": "বাংলা"}).json()["entries"][0]
    assert entry["id"] == accounts[1].pk
    assert (
        not {"password", "kindle_emails", "password_setup_nonce", "profile_image"}
        & entry.keys()
    )


@pytest.mark.parametrize(
    "parameters", [{"limit": 101}, {"page": 0}, {"status": "invalid"}, {"q": "a" * 201}]
)
def test_invalid_list_parameters_fail_with_field_errors(client, accounts, parameters):
    response = client.get(USERS, parameters)
    assert response.status_code == 400
    assert response.json()["field_errors"]


def test_readers_and_scoped_access_grants_do_not_enable_user_management(client):
    user = User.objects.create_user(email="scoped-access@library.test")
    book = Book.objects.create(title="বিশেষ বই")
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.ACCESS_MANAGE
    )
    client.force_login(user)
    assert (
        client.get(USERS).status_code
        == client.get(REFERENCES, {"kind": "book"}).status_code
        == 403
    )


def test_account_update_uses_revision_and_audits_only_identifiers(client, accounts):
    actor, target = accounts
    detail = client.get(account_url(target)).json()
    response = client.patch(
        account_url(target),
        {
            "expected_updated_at": detail["updated_at"],
            "full_name": "নতুন নাম",
            "is_active": False,
            "totp_required": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    target.refresh_from_db()
    assert (
        target.full_name == "নতুন নাম" and not target.is_active and target.totp_required
    )
    audit = AuditLog.objects.get(verb="account.update")
    assert (
        audit.actor == actor
        and audit.target_id == str(target.pk)
        and audit.payload == {}
    )
    assert (
        client.patch(
            account_url(target),
            {"expected_updated_at": detail["updated_at"], "is_active": True},
            content_type="application/json",
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "field", ["is_staff", "is_superuser", "email", "password", "global_scopes"]
)
def test_privilege_and_identity_fields_are_rejected(client, accounts, field):
    target = accounts[1]
    response = client.patch(
        account_url(target),
        {"expected_updated_at": target.updated_at.isoformat(), field: True},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert field in response.json()["field_errors"]


@pytest.mark.parametrize("role", ["self", "staff", "superuser", "full_control"])
def test_protected_accounts_cannot_be_changed_by_an_access_manager(
    client, accounts, role
):
    actor, target = accounts
    if role == "self":
        target = actor
    elif role == "full_control":
        PermissionGrant.objects.create(
            user=target, scope=PermissionScope.ADMIN_FULL_CONTROL
        )
    else:
        setattr(target, f"is_{role}", True)
        target.save()
    assert client.get(account_url(target)).json()["can_edit"] is False
    assert (
        client.patch(
            account_url(target),
            {"expected_updated_at": target.updated_at.isoformat(), "is_active": False},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert (
        client.post(
            account_url(target) + "grants/",
            grant_request(),
            content_type="application/json",
        ).status_code
        == 403
    )


def test_grants_are_idempotent_revocable_and_do_not_transfer_ownership(
    client, accounts
):
    target = accounts[1]
    book = Book.objects.create(title="শুধু এই বই")
    values = {**grant_request(), "book": str(book.pk)}
    endpoint = account_url(target) + "grants/"
    created = client.post(endpoint, values, content_type="application/json")
    assert created.status_code == 201
    grant = created.json()
    assert grant["effective"] is True and grant["target_type"] == "book"
    assert (
        client.post(endpoint, values, content_type="application/json").json()["id"]
        == grant["id"]
    )
    assert PermissionGrant.objects.filter(user=target).count() == 1
    assert not UserBook.objects.filter(user=target).exists()
    response = client.patch(
        endpoint + grant["id"] + "/",
        {"expected_updated_at": grant["updated_at"], "is_active": False},
        content_type="application/json",
    )
    assert response.status_code == 200 and response.json()["effective"] is False
    assert (
        client.patch(
            endpoint + grant["id"] + "/",
            {"expected_updated_at": grant["updated_at"], "is_active": True},
            content_type="application/json",
        ).status_code
        == 409
    )


def test_invalid_targets_scopes_and_opposing_read_permissions_fail(client, accounts):
    target = accounts[1]
    endpoint = account_url(target) + "grants/"
    book = Book.objects.create(title="লক্ষ্য বই")
    category = Category.objects.create(name="লক্ষ্য বিভাগ")
    cases = [
        {**grant_request(), "book": str(book.pk), "category": str(category.pk)},
        {**grant_request(PermissionScope.PROCESSING_MANAGE), "book": str(book.pk)},
        grant_request(PermissionScope.ADMIN_FULL_CONTROL),
    ]
    for values in cases:
        assert (
            client.post(endpoint, values, content_type="application/json").status_code
            == 400
        )
    assert (
        client.post(
            endpoint,
            grant_request(PermissionScope.READ_ONCE),
            content_type="application/json",
        ).status_code
        == 201
    )
    assert (
        client.post(
            endpoint, grant_request(), content_type="application/json"
        ).status_code
        == 400
    )


def test_duplicate_active_targets_and_colliding_ids_return_conflicts(client, accounts):
    endpoint = account_url(accounts[1]) + "grants/"
    values = grant_request()
    assert (
        client.post(endpoint, values, content_type="application/json").status_code
        == 201
    )
    assert (
        client.post(
            endpoint, grant_request(), content_type="application/json"
        ).status_code
        == 409
    )
    assert (
        client.post(
            endpoint,
            {**values, "notes": "বদলানো অনুরোধ"},
            content_type="application/json",
        ).status_code
        == 409
    )


def test_expired_and_revoked_permissions_have_honest_effective_status(client, accounts):
    target = accounts[1]
    PermissionGrant.objects.create(
        user=target,
        scope=PermissionScope.READ_ONCE,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    PermissionGrant.objects.create(
        user=target, scope=PermissionScope.SEND_KINDLE, is_active=False
    )
    entries = client.get(account_url(target) + "grants/").json()["entries"]
    assert len(entries) == 2 and all(not entry["effective"] for entry in entries)


def test_remote_selectors_exclude_deleted_books_and_non_authors(client, accounts):
    book = Book.objects.create(title="চয়নযোগ্য বই")
    Book.objects.create(title="অপসারিত বই", deleted_at=timezone.now())
    author = Contributor.objects.create(name="বাংলা লেখক")
    translator = Contributor.objects.create(name="বাংলা অনুবাদক")
    BookContributor.objects.create(book=book, contributor=author, role="author")
    BookContributor.objects.create(book=book, contributor=translator, role="translator")
    books = client.get(REFERENCES, {"kind": "book", "q": "বই"}).json()["entries"]
    authors = client.get(REFERENCES, {"kind": "author", "q": "বাংলা"}).json()["entries"]
    assert [entry["id"] for entry in books] == [str(book.pk)]
    assert [entry["id"] for entry in authors] == [str(author.pk)]
    assert (
        client.post(
            account_url(accounts[1]) + "grants/",
            {**grant_request(), "contributor": str(translator.pk)},
            content_type="application/json",
        ).status_code
        == 400
    )


def test_management_mutations_require_real_csrf(accounts):
    client = Client(enforce_csrf_checks=True)
    client.force_login(accounts[0])
    endpoint = account_url(accounts[1])
    values = {
        "expected_updated_at": accounts[1].updated_at.isoformat(),
        "full_name": "সুরক্ষিত নাম",
    }
    assert (
        client.patch(endpoint, values, content_type="application/json").status_code
        == 403
    )
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    assert (
        client.patch(
            endpoint, values, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )
