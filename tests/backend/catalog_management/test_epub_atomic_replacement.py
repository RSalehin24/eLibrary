from pathlib import Path

import pytest
from apps.access.models import Bookmark, PreviewAccessSession, ReadingSession
from apps.access.publication_models import PreparedPublication
from apps.access.reading.preparation import prepare_epub_asset
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset, MetadataVersion, UserBook
from apps.common.models import AuditLog
from django.utils import timezone

from ..access.reader_fixtures import write_epub
from .epub_upload_fixtures import send_upload

pytestmark = pytest.mark.django_db


def previous_edition(fixture):
    assert send_upload(fixture).status_code == 200
    fixture[1].refresh_from_db()
    return GeneratedAsset.objects.get(book=fixture[1], asset_type="epub")


def assert_previous_unchanged(asset):
    revision, file, checksum = asset.updated_at, asset.file.name, asset.checksum
    asset.refresh_from_db()
    assert (asset.updated_at, asset.file.name, asset.checksum) == (
        revision,
        file,
        checksum,
    )
    assert asset.book.state == "published"
    assert AuditLog.objects.filter(verb="catalog.epub.upload").count() == 1
    assert not MetadataVersion.objects.filter(source="before_epub_upload").exists()


def test_invalid_chapter_resource_does_not_replace_a_readable_edition(upload_book):
    asset = previous_edition(upload_book)
    write_epub(upload_book[3], {"OEBPS/chapter-1.xhtml": b"\xffinvalid utf-8"})
    response = send_upload(upload_book)
    assert response.status_code == 400 and response.json()["field_errors"]["file"]
    assert_previous_unchanged(asset)


@pytest.mark.parametrize("operation", ["storage", "reader"])
def test_storage_failure_preserves_the_published_edition(
    upload_book, monkeypatch, operation
):
    asset = previous_edition(upload_book)

    def unavailable(*arguments, **keywords):
        raise OSError("simulated storage failure")

    if operation == "storage":
        monkeypatch.setattr(asset.file.storage, "save", unavailable)
    else:
        write_epub(upload_book[3], {"OEBPS/chapter-1.xhtml": "<p>Updated chapter.</p>"})
        monkeypatch.setattr(
            "apps.access.reading.preparation.write_publication", unavailable
        )
    response = send_upload(upload_book)
    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    assert_previous_unchanged(asset)


@pytest.mark.parametrize("change,expected", [("revision", 409), ("authority", 404)])
def test_upload_rechecks_authority_and_revision_after_preparing(
    upload_book, monkeypatch, change, expected
):
    actor, book, _, _ = upload_book
    asset = previous_edition(upload_book)

    def prepare_then_change(candidate):
        publication = prepare_epub_asset(candidate)
        if change == "revision":
            Book.objects.filter(pk=book.pk).update(updated_at=timezone.now())
        else:
            User.objects.filter(pk=actor.pk).update(is_staff=False)
        return publication

    monkeypatch.setattr(
        "apps.catalog.editorial.epub_uploads.prepare_epub_asset", prepare_then_change
    )
    assert send_upload(upload_book).status_code == expected
    assert_previous_unchanged(asset)


def test_replacement_retains_reader_sessions_personal_data_and_protected_history(
    upload_book,
):
    actor, book, _, path = upload_book
    asset = previous_edition(upload_book)
    old_file = asset.file.path
    old_publication = PreparedPublication.objects.get(checksum=asset.checksum)
    session = PreviewAccessSession.objects.create(
        user=actor, book=book, prepared_publication=old_publication
    )
    progress = ReadingSession.objects.create(
        user=actor,
        book=book,
        preview_session=session,
        progress_percent=42,
        last_location="chapter-1.xhtml",
    )
    bookmark = Bookmark.objects.create(
        user=actor,
        book=book,
        location="chapter-1.xhtml",
        note="Keep this note",
        prepared_publication=old_publication,
    )
    UserBook.objects.create(user=actor, book=book)
    write_epub(
        path,
        {
            "OEBPS/chapter-1.xhtml": "<html><body><p>A revised chapter.</p></body></html>"
        },
    )
    assert send_upload(upload_book).status_code == 200
    asset.refresh_from_db()
    history = MetadataVersion.objects.get(source="before_epub_upload")
    assert history.snapshot["epub_asset"]["checksum"] == old_publication.checksum
    assert history.created_by == actor
    assert history.snapshot["epub_asset"]["file"] != asset.file.name
    assert Path(old_file).read_bytes()
    session.refresh_from_db()
    progress.refresh_from_db()
    bookmark.refresh_from_db()
    assert session.prepared_publication == old_publication
    assert progress.progress_percent == 42 and progress.preview_session == session
    assert (
        bookmark.note == "Keep this note"
        and bookmark.prepared_publication == old_publication
    )
    assert UserBook.objects.filter(user=actor, book=book).exists()
    assert PreparedPublication.objects.get(checksum=asset.checksum).state == "ready"


def test_new_manual_upload_is_ready_without_a_review_gate(upload_book):
    _, book, _, _ = upload_book
    book.state = "draft"
    book.save()
    response = send_upload(upload_book)
    assert response.status_code == 200
    assert response.json()["state"] == "published"
    assert "review_state" not in response.json()


def test_database_failure_rolls_back_the_entire_asset_switch(upload_book, monkeypatch):
    asset = previous_edition(upload_book)

    def reject_audit(*arguments, **keywords):
        raise OSError("simulated audit storage failure")

    monkeypatch.setattr(
        "apps.catalog.editorial.epub_uploads.AuditLog.objects.create", reject_audit
    )
    assert send_upload(upload_book).status_code == 503
    assert_previous_unchanged(asset)
