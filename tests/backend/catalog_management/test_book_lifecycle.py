from pathlib import Path

import pytest
from apps.access.models import Bookmark, PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, MetadataVersion, UserBook
from apps.common.models import AuditLog
from apps.processing.job_models import BackgroundJob
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from ..access.reader_fixtures import prepared_asset

pytestmark = pytest.mark.django_db


@pytest.fixture
def managed_book(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    actor = User.objects.create_user(
        email="lifecycle-admin@library.test", is_staff=True
    )
    book = Book.objects.create(
        title="বই পরিচালনার পরীক্ষা", state="published", indexing_eligible=True
    )
    asset, publication = prepared_asset(book, tmp_path)
    client = APIClient()
    client.force_authenticate(actor)
    return actor, book, client, asset, publication


def book_url(book):
    return f"/api/v1/manage/books/{book.slug}/"


def test_controls_and_editor_share_the_exact_revision_representation(managed_book):
    _, book, client, _, _ = managed_book
    detail = client.get(book_url(book)).json()
    controls = client.get(book_url(book) + "controls/").json()
    assert controls["book_revision"] == detail["updated_at"]


def test_removal_keeps_files_and_personal_records_but_blocks_new_book_access(
    managed_book,
):
    actor, book, client, asset, publication = managed_book
    UserBook.objects.create(user=actor, book=book)
    bookmark = Bookmark.objects.create(
        user=actor, book=book, location="chapter:0:0", prepared_publication=publication
    )
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    path = Path(asset.legacy_path)
    response = client.delete(
        book_url(book),
        {"expected_updated_at": book.updated_at.isoformat()},
        format="json",
    )
    assert (
        response.status_code == 204 and response["Cache-Control"] == "private, no-store"
    )
    book.refresh_from_db()
    assert book.deleted_at and book.state == "soft_deleted" and path.is_file()
    assert UserBook.objects.filter(user=actor, book=book).exists()
    assert Bookmark.objects.filter(pk=bookmark.pk).exists()
    assert AuditLog.objects.get(verb="catalog.book.remove").actor == actor
    assert MetadataVersion.objects.filter(book=book, source="editorial").exists()
    assert client.get(book_url(book)).status_code == 404
    assert client.get(f"/api/v1/catalog/books/{book.slug}/").status_code == 404
    assert client.get(f"/api/v1/reading/sessions/{session['id']}/").status_code == 404
    assert client.get(f"/api/v1/me/bookmarks/{bookmark.pk}/").status_code == 200


@pytest.mark.parametrize(
    "state", ["queued", "running", "retry_wait", "paused", "needs_attention"]
)
def test_unfinished_work_blocks_removal_without_changing_records(managed_book, state):
    actor, book, client, asset, _ = managed_book
    BackgroundJob.objects.create(
        requested_by=actor,
        book=book,
        asset=asset,
        kind="prepare_epub",
        state=state,
        available_at=timezone.now(),
    )
    controls = client.get(book_url(book) + "controls/").json()
    assert controls["can_remove"] is False and controls["active_operation_id"]
    assert (
        client.delete(
            book_url(book),
            {"expected_updated_at": book.updated_at.isoformat()},
            format="json",
        ).status_code
        == 409
    )
    book.refresh_from_db()
    assert book.deleted_at is None and book.state == "published"
    assert not AuditLog.objects.exists()


def test_stale_or_unknown_removal_fields_leave_the_book_unchanged(managed_book):
    _, book, client, _, _ = managed_book
    for values in [
        {"expected_updated_at": "2020-01-01T00:00:00Z"},
        {"expected_updated_at": book.updated_at.isoformat(), "permanent": True},
    ]:
        assert client.delete(book_url(book), values, format="json").status_code in {
            400,
            409,
        }
    book.refresh_from_db()
    assert book.deleted_at is None


def test_metadata_scope_cannot_remove_any_book(managed_book):
    _, book, client, _, _ = managed_book
    editor = User.objects.create_user(email="lifecycle-editor@library.test")
    other = Book.objects.create(title="Unrelated book")
    PermissionGrant.objects.create(
        user=editor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    client.force_authenticate(editor)
    assert client.get(book_url(book) + "controls/").status_code == 404
    assert (
        client.delete(
            book_url(other),
            {"expected_updated_at": other.updated_at.isoformat()},
            format="json",
        ).status_code
        == 404
    )
    assert (
        client.delete(
            book_url(book),
            {"expected_updated_at": book.updated_at.isoformat()},
            format="json",
        ).status_code
        == 404
    )


def test_removal_requires_csrf_and_rejects_disabled_accounts(managed_book):
    actor, book, _, _, _ = managed_book
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    assert (
        client.delete(
            book_url(book),
            {"expected_updated_at": book.updated_at.isoformat()},
            content_type="application/json",
        ).status_code
        == 403
    )
    actor.is_active = False
    actor.save()
    assert client.get(book_url(book) + "controls/").status_code == 403


def test_uploaded_books_without_source_have_explanatory_regeneration_state(
    managed_book,
):
    _, book, client, _, _ = managed_book
    controls = client.get(book_url(book) + "controls/").json()
    assert (
        not controls["can_regenerate"]
        and controls["regeneration_problem"] == "source_unavailable"
    )

    book.save()
    assert (
        client.get(book_url(book) + "controls/").json()["regeneration_problem"]
        == "source_unavailable"
    )
