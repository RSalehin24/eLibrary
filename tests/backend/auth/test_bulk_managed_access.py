from datetime import timedelta
from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, BookContributor, Contributor
from apps.common.models import AuditLog
from django.test import Client
from django.utils import timezone

from .managed_access_fixtures import account_url, grant_request

pytestmark = pytest.mark.django_db


def submit(client, target, entries):
    return client.post(
        account_url(target) + "grants/bulk/",
        {"entries": entries},
        content_type="application/json",
    )


def test_multiple_scopes_and_books_create_audited_permissions_without_ownership(
    client, accounts
):
    actor, target = accounts
    books = [Book.objects.create(title=f"বই {index}") for index in range(2)]
    entries = [
        {**grant_request(scope), "book": str(book.pk)}
        for book in books
        for scope in (PermissionScope.READ_DURABLE, PermissionScope.DOWNLOAD_FILE)
    ]
    response = submit(client, target, entries)
    assert response.status_code == 200
    result = response.json()
    assert result["created_count"] == 4 and result["rejected_count"] == 0
    assert [entry["index"] for entry in result["entries"]] == list(range(4))
    assert all(entry["status"] == "created" for entry in result["entries"])
    assert PermissionGrant.objects.filter(user=target, granted_by=actor).count() == 4
    assert AuditLog.objects.filter(actor=actor, verb="permission.create").count() == 4
    assert not target.my_books.exists()
    assert response["Cache-Control"] == "private, no-store"


def test_replaying_a_bulk_write_is_idempotent_and_does_not_resurrect_revoked_grants(
    client, accounts
):
    entries = [grant_request(PermissionScope.SEND_KINDLE), grant_request()]
    first = submit(client, accounts[1], entries).json()
    PermissionGrant.objects.filter(pk=entries[0]["id"]).update(is_active=False)
    second = submit(client, accounts[1], entries).json()
    assert first["created_count"] == second["existing_count"] == 2
    assert second["created_count"] == 0
    assert second["entries"][0]["grant"]["is_active"] is False
    assert PermissionGrant.objects.filter(user=accounts[1]).count() == 2
    assert AuditLog.objects.filter(verb="permission.create").count() == 2


def test_bad_items_do_not_rollback_successes_and_include_actionable_field_errors(
    client, accounts
):
    book = Book.objects.create(title="উপলব্ধ বই")
    entries = [
        grant_request(),
        {**grant_request(), "book": str(uuid4())},
        {**grant_request(PermissionScope.PROCESSING_MANAGE), "book": str(book.pk)},
        {**grant_request(PermissionScope.SEND_KINDLE), "unexpected": True},
    ]
    result = submit(client, accounts[1], entries).json()
    assert result["created_count"] == 1 and result["rejected_count"] == 3
    assert [item["status"] for item in result["entries"]] == [
        "created",
        "invalid",
        "invalid",
        "invalid",
    ]
    assert all(item["field_errors"] for item in result["entries"][1:])
    assert PermissionGrant.objects.filter(user=accounts[1]).count() == 1


def test_active_duplicates_and_opposing_read_scopes_are_reported_per_item(
    client, accounts
):
    entries = [
        grant_request(),
        grant_request(),
        grant_request(PermissionScope.READ_ONCE),
    ]
    result = submit(client, accounts[1], entries).json()
    assert [item["status"] for item in result["entries"]] == [
        "created",
        "conflict",
        "invalid",
    ]
    assert result["entries"][1]["code"] == "state_conflict"
    assert PermissionGrant.objects.filter(user=accounts[1]).count() == 1


@pytest.mark.parametrize(
    "entries", [[], [grant_request()] * 2, [grant_request() for _ in range(101)]]
)
def test_invalid_batch_envelopes_write_nothing(client, accounts, entries):
    response = submit(client, accounts[1], entries)
    assert response.status_code == 400 and response.json()["field_errors"]["entries"]
    assert not PermissionGrant.objects.filter(user=accounts[1]).exists()


def test_malformed_item_id_is_a_partial_validation_result(client, accounts):
    response = submit(
        client,
        accounts[1],
        [{"id": "invalid", "scope": "read:durable"}, grant_request()],
    )
    assert response.status_code == 200
    result = response.json()
    assert result["entries"][0]["id"] is None
    assert result["entries"][0]["field_errors"]["id"]
    assert result["created_count"] == result["rejected_count"] == 1


def test_changed_replay_is_a_conflict_and_keeps_original_permission(client, accounts):
    entry = grant_request()
    submit(client, accounts[1], [entry])
    result = submit(client, accounts[1], [{**entry, "notes": "পরিবর্তিত"}]).json()
    assert result["entries"][0]["status"] == "conflict"
    assert PermissionGrant.objects.get(pk=entry["id"]).notes == entry["notes"]


def test_author_and_expiry_rules_match_single_grant_validation(client, accounts):
    book = Book.objects.create(title="একটি বই")
    writer = Contributor.objects.create(name="লেখক")
    translator = Contributor.objects.create(name="অনুবাদক")
    BookContributor.objects.create(book=book, contributor=writer, role="author")
    BookContributor.objects.create(book=book, contributor=translator, role="translator")
    expiry = (timezone.now() + timedelta(hours=1)).isoformat()
    entries = [
        {**grant_request(), "contributor": str(person.pk), "expires_at": expiry}
        for person in (writer, translator)
    ]
    result = submit(client, accounts[1], entries).json()
    assert [item["status"] for item in result["entries"]] == ["created", "invalid"]
    assert result["entries"][0]["grant"]["expires_at"] is not None


@pytest.mark.parametrize("target_kind", ["self", "staff", "superuser"])
def test_protected_accounts_reject_whole_batch_before_any_write(
    client, accounts, target_kind
):
    target = (
        accounts[0]
        if target_kind == "self"
        else User.objects.create_user(
            email=f"protected-bulk-{target_kind}@library.test",
            is_staff=target_kind == "staff",
            is_superuser=target_kind == "superuser",
        )
    )
    count = PermissionGrant.objects.count()
    assert submit(client, target, [grant_request()]).status_code == 403
    assert PermissionGrant.objects.count() == count


def test_readers_and_scoped_managers_cannot_grant_in_bulk(client, accounts):
    reader = User.objects.create_user(email="bulk-reader@library.test")
    PermissionGrant.objects.create(
        user=reader,
        book=Book.objects.create(title="বই"),
        scope=PermissionScope.ACCESS_MANAGE,
    )
    client.force_login(reader)
    assert submit(client, accounts[1], [grant_request()]).status_code == 403
    assert not PermissionGrant.objects.filter(user=accounts[1]).exists()


def test_bulk_mutations_enforce_csrf(accounts):
    client = Client(enforce_csrf_checks=True)
    client.force_login(accounts[0])
    assert submit(client, accounts[1], [grant_request()]).status_code == 403
    assert not PermissionGrant.objects.filter(user=accounts[1]).exists()
