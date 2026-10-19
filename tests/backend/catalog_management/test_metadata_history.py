import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, MetadataVersion
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def editor():
    actor = User.objects.create_user(
        email="history-editor@library.test", full_name="History Editor"
    )
    book = Book.objects.create(title="আগের নাম")
    PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.METADATA_EDIT, book=book
    )
    client = APIClient()
    client.force_authenticate(actor)
    return client, actor, book


def history_path(book):
    return f"/api/v1/manage/books/{book.slug}/history/"


def test_edit_note_is_recorded_with_previous_metadata_and_actor(editor):
    client, actor, book = editor
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/",
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "title": "নতুন নাম",
            "edit_note": "  Corrected the title spelling.  ",
        },
        format="json",
    )
    assert response.status_code == 200
    version = MetadataVersion.objects.get(book=book)
    assert version.notes == "Corrected the title spelling."
    assert version.snapshot["title"] == "আগের নাম"
    assert version.created_by == actor and version.source == "editorial"
    book.refresh_from_db()
    assert not hasattr(book, "edit_note")
    response = client.get(history_path(book))
    assert response.json()["entries"][0]["created_by"] == {
        "id": actor.pk,
        "name": "History Editor",
    }


def test_history_is_paginated_stable_and_excludes_private_snapshot_fields(editor):
    client, actor, book = editor
    timestamp = timezone.now()
    for index in range(3):
        version = MetadataVersion.objects.create(
            book=book,
            created_by=actor,
            notes=f"Change {index}",
            snapshot={"main_content_html": "PRIVATE BOOK TEXT", "secret": "PRIVATE"},
        )
        MetadataVersion.objects.filter(pk=version.pk).update(created_at=timestamp)
    expected = list(book.metadata_versions.order_by("-created_at", "-id"))
    first = client.get(f"{history_path(book)}?limit=2")
    second = client.get(f"{history_path(book)}?limit=2&page=2")
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["pagination"] == {"page": 1, "limit": 2, "total_count": 3}
    identifiers = [
        entry["id"] for entry in first.json()["entries"] + second.json()["entries"]
    ]
    assert identifiers == [str(version.pk) for version in expected]
    assert "PRIVATE" not in first.content.decode()
    assert "snapshot" not in first.content.decode()
    assert actor.email not in first.content.decode()
    assert first["Cache-Control"].startswith("private")


def test_history_requires_matching_active_metadata_permission(editor):
    client, actor, book = editor
    unrelated = Book.objects.create(title="অন্য বই")
    MetadataVersion.objects.create(book=unrelated, notes="UNRELATED PRIVATE HISTORY")
    assert client.get(history_path(unrelated)).status_code == 404
    assert APIClient().get(history_path(book)).status_code == 403
    PermissionGrant.objects.filter(user=actor).update(is_active=False)
    assert client.get(history_path(book)).status_code == 404


def test_history_handles_automated_versions_and_old_slugs(editor):
    client, _, book = editor
    MetadataVersion.objects.create(book=book, source="curated")
    path = history_path(book)
    book.title = "নতুন বইয়ের নাম"
    book.save()
    response = client.get(path)
    assert response.status_code == 200
    assert response.json()["entries"][0]["created_by"] is None
    assert response.json()["entries"][0]["source"] == "curated"


def test_removed_books_do_not_expose_history(editor):
    client, _, book = editor
    book.deleted_at = timezone.now()
    book.save(update_fields=["deleted_at", "updated_at"])
    assert client.get(history_path(book)).status_code == 404


@pytest.mark.parametrize("query", ["limit=101", "limit=0", "page=0", "page=oops"])
def test_invalid_history_page_parameters_are_rejected(editor, query):
    client, _, book = editor
    assert client.get(f"{history_path(book)}?{query}").status_code == 400


@pytest.mark.parametrize("note", ["x" * 2001, {"invalid": "value"}])
def test_invalid_edit_notes_do_not_write_versions(editor, note):
    client, _, book = editor
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/",
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "summary": "Changed",
            "edit_note": note,
        },
        format="json",
    )
    assert response.status_code == 400
    assert "edit_note" in response.json()["field_errors"]
    assert not MetadataVersion.objects.exists()


def test_note_alone_does_not_create_an_empty_revision(editor):
    client, _, book = editor
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/",
        {"expected_updated_at": book.updated_at.isoformat(), "edit_note": "No change"},
        format="json",
    )
    assert response.status_code == 400
    assert not MetadataVersion.objects.exists()


def test_stale_edit_note_cannot_be_attached_to_a_newer_revision(editor):
    client, _, book = editor
    previous_updated_at = book.updated_at.isoformat()
    book.summary = "Newer change"
    book.save()
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/",
        {
            "expected_updated_at": previous_updated_at,
            "summary": "Stale",
            "edit_note": "Stale note",
        },
        format="json",
    )
    assert response.status_code == 409
    assert not MetadataVersion.objects.exists()


def test_relationship_edit_note_is_recorded(editor):
    client, actor, book = editor
    actor.is_staff = True
    actor.save()
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/relationships/",
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "category_ids": [],
            "edit_note": "Removed incorrect categories",
        },
        format="json",
    )
    assert response.status_code == 200
    version = MetadataVersion.objects.get(book=book)
    assert version.source == "editorial-relationships"
    assert version.notes == "Removed incorrect categories"
    assert version.created_by == actor
