from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.editorial.service import update_book_editorial
from apps.catalog.models import Book, MetadataVersion, UserBook
from apps.common.permissions import is_book_administrator
from django.http import Http404
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def actor_for_case(case, book):
    actor = User.objects.create_user(email=f"{case}@library.test")
    if case in {"staff", "inactive", "totp"}:
        actor.is_staff = True
    if case == "superuser":
        actor.is_superuser = True
    actor.is_active = case != "inactive"
    actor.totp_required = case == "totp"
    actor.save()
    if case == "owner":
        UserBook.objects.create(user=actor, book=book)
    if case in {
        "global_metadata",
        "scoped_metadata",
        "scoped_admin",
        "global_admin",
        "expired",
        "revoked",
    }:
        PermissionGrant.objects.create(
            user=actor,
            scope=PermissionScope.METADATA_EDIT
            if "metadata" in case
            else PermissionScope.ADMIN_FULL_CONTROL,
            book=book if case.startswith("scoped") else None,
            expires_at=timezone.now() - timedelta(seconds=1)
            if case == "expired"
            else None,
            is_active=case != "revoked",
        )
    return actor


@pytest.mark.parametrize(
    "case",
    [
        "reader",
        "owner",
        "global_metadata",
        "scoped_metadata",
        "scoped_admin",
        "global_admin",
        "expired",
        "revoked",
        "staff",
        "superuser",
        "inactive",
        "totp",
    ],
)
def test_book_administration_capability_and_direct_writes_use_the_same_policy(case):
    book = Book.objects.create(title="অপরিবর্তিত বই", state="published")
    actor = actor_for_case(case, book)
    permitted = case in {"staff", "superuser", "global_admin"}
    assert is_book_administrator(actor) is permitted
    client = APIClient()
    client.force_authenticate(actor)
    access = client.get(f"/api/v1/reading/books/{book.slug}/access/")
    if case not in {"inactive", "totp"}:
        assert access.status_code == 200
        assert access.json()["can_edit_book"] is permitted
    fields = {"expected_updated_at": book.updated_at.isoformat(), "summary": "পরিবর্তন"}
    response = client.patch(f"/api/v1/manage/books/{book.slug}/", fields, format="json")
    assert (response.status_code == 200) is permitted
    book.refresh_from_db()
    assert book.summary == ("পরিবর্তন" if permitted else "")
    assert MetadataVersion.objects.exists() is permitted


def test_global_metadata_intake_does_not_grant_existing_book_edit_access():
    book = Book.objects.create(title="আগের বই")
    actor = actor_for_case("global_metadata", book)
    client = APIClient()
    client.force_authenticate(actor)
    workspace = client.get("/api/v1/auth/session/").json()["workspaces"]
    assert (
        workspace["can_create_books"] is True and workspace["can_edit_books"] is False
    )
    fields = {"expected_updated_at": book.updated_at, "summary": "forbidden"}
    with pytest.raises(Http404):
        update_book_editorial(actor, book.pk, fields)
    assert not MetadataVersion.objects.exists()


def test_revocation_after_form_load_is_rechecked_under_the_actor_lock():
    book = Book.objects.create(title="ফর্ম খোলা বই")
    actor = actor_for_case("global_admin", book)
    stale_actor = User.objects.get(pk=actor.pk)
    PermissionGrant.objects.filter(user=actor).update(is_active=False)
    with pytest.raises(Http404):
        update_book_editorial(
            stale_actor,
            book.pk,
            {"expected_updated_at": book.updated_at, "summary": "forbidden"},
        )
    book.refresh_from_db()
    assert book.summary == "" and not MetadataVersion.objects.exists()
