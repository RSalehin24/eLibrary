import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.access.reading.preparation import prepare_epub_asset
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset, UserBook
from apps.common.models import AuditLog
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import SOURCE_ACTIVE_STATES, BackgroundJob
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connections
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from ..access.reader_fixtures import write_epub

pytestmark = pytest.mark.django_db


@pytest.fixture
def upload_book(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    actor = User.objects.create_user(email="upload-admin@library.test", is_staff=True)
    book = Book.objects.create(
        title="আপলোডের বই", state="published", review_state="approved"
    )
    client = APIClient()
    client.force_authenticate(actor)
    return actor, book, client, write_epub(tmp_path / "book.epub")


def upload_url(book):
    return f"/api/v1/manage/books/{book.slug}/epub/"


def send_upload(fixture, **changes):
    _, book, client, path = fixture
    values = {
        "expected_updated_at": book.updated_at.isoformat(),
        "file": SimpleUploadedFile(
            "book.epub", path.read_bytes(), "application/epub+zip"
        ),
        **changes,
    }
    return client.post(upload_url(book), values, format="multipart")


def test_uploaded_epub_is_private_reviewable_and_prepares_for_reading(upload_book):
    actor, book, _, path = upload_book
    response = send_upload(upload_book)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert response.json()["state"] == "needs_review"
    assert response.json()["editorial_reviewed_at"] is None
    asset = GeneratedAsset.objects.get(book=book, asset_type="epub")
    assert asset.checksum == hashlib.sha256(path.read_bytes()).hexdigest()
    assert asset.is_protected and asset.status == "ready" and not asset.source_job
    assert asset.content_type == "application/epub+zip"
    publication = prepare_epub_asset(asset)
    assert publication.state == "ready" and len(publication.manifest["chapters"]) == 2
    assert not UserBook.objects.exists() and not PermissionGrant.objects.exists()
    assert AuditLog.objects.get(verb="catalog.epub.upload").actor == actor


def test_replacement_preserves_old_bytes_and_stale_uploads_change_nothing(upload_book):
    _, book, _, _ = upload_book
    assert send_upload(upload_book).status_code == 200
    original = GeneratedAsset.objects.get(book=book)
    old_path, checksum = Path(original.file.path), original.checksum
    assert send_upload(upload_book).status_code == 409
    book.refresh_from_db()
    assert send_upload(upload_book).status_code == 200
    original.refresh_from_db()
    assert Path(original.file.path) != old_path and old_path.exists()
    assert original.checksum == checksum and AuditLog.objects.count() == 2


@pytest.mark.parametrize(
    "filename,content", [("book.pdf", b"PDF"), ("book.epub", b"not a zip")]
)
def test_upload_rejects_wrong_formats_without_creating_assets(
    upload_book, filename, content
):
    response = send_upload(upload_book, file=SimpleUploadedFile(filename, content))
    assert response.status_code == 400 and response.json()["field_errors"]["file"]
    assert not GeneratedAsset.objects.exists() and not AuditLog.objects.exists()


@pytest.mark.parametrize(
    "override",
    [
        {"../escape.xhtml": "unsafe path"},
        {"META-INF/container.xml": "<!DOCTYPE x [<!ENTITY y 'z'>]><container/>"},
        {"OEBPS/package.opf": "<package/>"},
    ],
)
def test_upload_reuses_archive_path_and_metadata_validation(upload_book, override):
    path = upload_book[3]
    write_epub(path, override)
    assert send_upload(upload_book).status_code == 400
    assert not GeneratedAsset.objects.exists()


def test_upload_size_is_checked_before_opening_the_archive(upload_book, monkeypatch):
    monkeypatch.setattr("apps.catalog.editorial.epub_uploads.MAX_MANUAL_EPUB_BYTES", 10)
    response = send_upload(upload_book)
    assert (
        response.status_code == 400
        and "24 MiB" in response.json()["field_errors"]["file"][0]
    )
    assert not GeneratedAsset.objects.exists()


def test_upload_requires_metadata_authority_for_the_specific_book(upload_book):
    _, book, client, _ = upload_book
    client.force_authenticate(None)
    assert send_upload(upload_book).status_code == 403
    editor = User.objects.create_user(email="upload-editor@library.test")
    client.force_authenticate(editor)
    assert send_upload(upload_book).status_code == 404
    PermissionGrant.objects.create(
        user=editor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    assert send_upload(upload_book).status_code == 200


@pytest.mark.parametrize("state", SOURCE_ACTIVE_STATES)
def test_upload_cannot_race_an_unfinished_source_operation(upload_book, state):
    actor, book, _, _ = upload_book
    entry = SourceCatalogEntry.objects.create(
        source_url="https://source.test/books/example/", title=book.title
    )
    BackgroundJob.objects.create(
        requested_by=actor,
        book=book,
        source_record=entry,
        kind="process_source",
        state=state,
        available_at=timezone.now(),
    )
    assert send_upload(upload_book).status_code == 409
    assert not GeneratedAsset.objects.exists()


def test_paper_records_reject_files_and_unknown_fields_are_not_ignored(upload_book):
    _, book, _, _ = upload_book
    assert send_upload(upload_book, publish=True).status_code == 400
    book.record_type = "manual"
    book.save()
    assert send_upload(upload_book).status_code == 400
    assert not GeneratedAsset.objects.exists()


def test_session_upload_requires_csrf_before_any_mutation(upload_book):
    actor, book, _, path = upload_book
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    response = client.post(
        upload_url(book),
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "file": SimpleUploadedFile("book.epub", path.read_bytes()),
        },
    )
    assert response.status_code == 403 and "CSRF" in response.json()["detail"]
    assert not GeneratedAsset.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_uploads_publish_one_asset_revision(upload_book):
    actor, book, _, path = upload_book
    start = Barrier(2)

    def upload_once():
        close_old_connections()
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=actor.pk))
        try:
            start.wait(timeout=10)
            return send_upload((actor, book, client, path)).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(upload_once) for _ in range(2)]
        assert sorted(result.result(timeout=20) for result in futures) == [200, 409]
    assert GeneratedAsset.objects.count() == AuditLog.objects.count() == 1
