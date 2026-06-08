from pathlib import Path
from smtplib import SMTPAuthenticationError
from urllib.parse import quote

import pytest
from bs4 import BeautifulSoup
from django.core import mail
from django.core.files.base import ContentFile
from django.test import override_settings

from apps.access.models import PermissionGrant, PermissionScope, PreviewAccessSession
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    Category,
    Contributor,
    ContributorRole,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.common.permissions import user_has_scope
from apps.ingestion.models import BookSubmission, ResolutionStatus, SubmissionStatus
from apps.access.views import normalize_preview_book_sections


def assert_content_disposition_filename(header_value, expected_filename):
    assert (
        f'filename="{expected_filename}"' in header_value
        or f"filename*=utf-8''{quote(expected_filename)}" in header_value
    )


@pytest.mark.django_db
def test_download_and_reader_launch_are_protected(tmp_path, client):
    user = User.objects.create_user(email="access@example.com", password="strong-password-123")
    book = Book.objects.create(title="Access Book", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "access-book.epub"
    html_path = Path(tmp_path) / "book.html"
    epub_path.write_bytes(b"epub")
    html_path.write_text("<html></html>", encoding="utf-8")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )

    client.force_login(user)
    denied = client.get(f"/api/access/books/{book.slug}/download/epub/")
    assert denied.status_code == 403

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.DOWNLOAD_FILE)
    allowed = client.get(f"/api/access/books/{book.slug}/download/epub/")
    assert allowed.status_code == 200
    assert_content_disposition_filename(allowed.headers["Content-Disposition"], "Access Book.epub")

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.PREVIEW_HTML)
    launch = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert launch.status_code == 200

    manifest_url = launch.json()["manifest_url"]
    manifest_path = manifest_url.replace("http://testserver", "")
    manifest = client.get(manifest_path)
    assert manifest.status_code == 200
    assert manifest.json()["book"]["slug"] == book.slug
    assert manifest.json()["reading_session_url"]
    assert manifest.json()["bookmarks_url"]


@pytest.mark.django_db
def test_book_owner_can_access_cover_downloads_and_reader_without_explicit_grants(tmp_path, client):
    user = User.objects.create_user(email="owner-access@example.com", password="strong-password-123")
    book = Book.objects.create(title="Owned Book", state="ready", review_state="approved")
    cover_path = Path(tmp_path) / "book_cover.jpg"
    html_path = Path(tmp_path) / "book.html"
    epub_path = Path(tmp_path) / "owned-book.epub"
    cover_path.write_bytes(b"cover")
    html_path.write_text("<html></html>", encoding="utf-8")
    epub_path.write_bytes(b"epub")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.COVER,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(cover_path),
        content_type="image/jpeg",
        file_size=cover_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.ebanglalibrary.com/books/owned-book/",
        normalized_input="https://www.ebanglalibrary.com/books/owned-book/",
        resolved_url="https://www.ebanglalibrary.com/books/owned-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.READY,
        linked_book=book,
    )

    client.force_login(user)

    list_response = client.get("/api/catalog/books/?ownership=mine")
    assert list_response.status_code == 200
    assert list_response.json()[0]["cover_download_url"].endswith(f"/api/access/books/{book.slug}/download/cover/")

    detail_response = client.get(f"/api/catalog/books/{book.slug}/")
    assert detail_response.status_code == 200
    asset_urls = {asset["asset_type"]: asset["download_url"] for asset in detail_response.json()["assets"]}
    assert asset_urls["cover"].endswith(f"/api/access/books/{book.slug}/download/cover/")
    assert asset_urls["html"].endswith(f"/api/access/books/{book.slug}/download/html/")
    assert asset_urls["epub"].endswith(f"/api/access/books/{book.slug}/download/epub/")

    cover_response = client.get(f"/api/access/books/{book.slug}/download/cover/")
    html_response = client.get(f"/api/access/books/{book.slug}/download/html/")
    epub_response = client.get(f"/api/access/books/{book.slug}/download/epub/")
    assert cover_response.status_code == 200
    assert html_response.status_code == 200
    assert epub_response.status_code == 200

    launch = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert launch.status_code == 200


@pytest.mark.django_db
def test_download_uses_current_book_title_for_cover_and_epub_filenames(tmp_path, client):
    user = User.objects.create_user(email="filename-access@example.com", password="strong-password-123")
    book = Book.objects.create(title="বর্তমান বই নাম", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "মযলস.epub"
    cover_path = Path(tmp_path) / "book_cover.jpg"
    epub_path.write_bytes(b"epub")
    cover_path.write_bytes(b"cover")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.COVER,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(cover_path),
        content_type="image/jpeg",
        file_size=cover_path.stat().st_size,
    )

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.DOWNLOAD_FILE)
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.PREVIEW_HTML)
    client.force_login(user)

    epub_response = client.get(f"/api/access/books/{book.slug}/download/epub/")
    cover_response = client.get(f"/api/access/books/{book.slug}/download/cover/")
    assert epub_response.status_code == 200
    assert cover_response.status_code == 200
    assert_content_disposition_filename(epub_response.headers["Content-Disposition"], "বর্তমান বই নাম.epub")
    assert_content_disposition_filename(cover_response.headers["Content-Disposition"], "বর্তমান বই নাম.jpg")

    launch = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    manifest_path = launch.json()["manifest_url"].replace("http://testserver", "")
    manifest = client.get(manifest_path)
    reader_epub_path = manifest.json()["epub_download_url"].replace("http://testserver", "")
    reader_epub_response = client.get(reader_epub_path)
    assert reader_epub_response.status_code == 200
    assert_content_disposition_filename(reader_epub_response.headers["Content-Disposition"], "বর্তমান বই নাম.epub")


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ACCOUNT_INVITE_FROM_EMAIL="kindle-sender@example.com",
)
def test_book_can_be_sent_to_all_configured_kindle_emails(tmp_path, client):
    user = User.objects.create_user(
        email="kindle-reader@example.com",
        password="strong-password-123",
        kindle_emails=["reader-one@kindle.com", "reader-two@kindle.com"],
    )
    book = Book.objects.create(title="Kindle Delivery Book", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "kindle-delivery.epub"
    epub_path.write_bytes(b"epub")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.SEND_KINDLE)
    client.force_login(user)

    response = client.post(f"/api/access/books/{book.slug}/send-to-kindle/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deliveredEmails"] == user.kindle_emails
    assert payload["failedEmails"] == []
    assert payload["senderEmail"] == "kindle-sender@example.com"
    assert all(message.body == "" for message in mail.outbox)
    assert all(message.attachments[0][0] == "Kindle Delivery Book.epub" for message in mail.outbox)


@pytest.mark.django_db
def test_read_once_permission_blocks_subsequent_launches(tmp_path, client):
    user = User.objects.create_user(email="once-reader@example.com", password="strong-password-123")
    book = Book.objects.create(title="Read Once Book", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "read-once.epub"
    epub_path.write_bytes(b"epub")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.READ_ONCE)
    client.force_login(user)

    # First launch should succeed
    response = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response.status_code == 200

    # Second launch should fail
    response2 = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response2.status_code == 403


@pytest.mark.django_db
def test_read_once_permission_blocks_html_previews(tmp_path, client):
    user = User.objects.create_user(email="once-html-reader@example.com", password="strong-password-123")
    book = Book.objects.create(title="Read Once HTML Book", state="ready", review_state="approved")
    html_path = Path(tmp_path) / "preview.html"
    html_path.write_text("<html></html>", encoding="utf-8")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.READ_ONCE)
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.PREVIEW_HTML)
    client.force_login(user)

    # First HTML download should succeed
    response = client.get(f"/api/access/books/{book.slug}/download/html/")
    assert response.status_code == 200

    # Second HTML download should fail
    response2 = client.get(f"/api/access/books/{book.slug}/download/html/")
    assert response2.status_code == 403


@pytest.mark.django_db
def test_read_once_html_preview_blocks_reader_launch(tmp_path, client):
    user = User.objects.create_user(email="once-cross-reader@example.com", password="strong-password-123")
    book = Book.objects.create(title="Cross Read Book", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "cross.epub"
    html_path = Path(tmp_path) / "cross.html"
    epub_path.write_bytes(b"epub")
    html_path.write_text("<html></html>", encoding="utf-8")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.READ_ONCE)
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.PREVIEW_HTML)
    client.force_login(user)

    # First download HTML preview
    response = client.get(f"/api/access/books/{book.slug}/download/html/")
    assert response.status_code == 200

    # Reader launch is now blocked
    response2 = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response2.status_code == 403


@pytest.mark.django_db
def test_read_once_without_preview_html_permission_cannot_view_html(tmp_path, client):
    user = User.objects.create_user(email="once-no-html@example.com", password="strong-password-123")
    book = Book.objects.create(title="No HTML Book", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "no-html.epub"
    html_path = Path(tmp_path) / "no-html.html"
    epub_path.write_bytes(b"epub")
    html_path.write_text("<html></html>", encoding="utf-8")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.READ_ONCE)
    client.force_login(user)

    # Cannot download HTML preview because preview_html permission is missing
    response = client.get(f"/api/access/books/{book.slug}/download/html/")
    assert response.status_code == 403

    # But can launch reader once!
    response2 = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response2.status_code == 200

    # Relaunching reader is now blocked
    response3 = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response3.status_code == 403


@pytest.mark.django_db
def test_read_once_mutual_exclusion_validation(client):
    from apps.accounts.serializers.managed_users import ManagedUserCreateSerializer
    from rest_framework import serializers

    # Try creating user with both global scopes
    serializer = ManagedUserCreateSerializer(
        data={
            "email": "mutual-fail@example.com",
            "password": "strong-password-123",
            "global_scopes": ["read:once", "read:durable"],
        }
    )
    assert serializer.is_valid() is False
    assert "global_scopes" in serializer.errors

    # Try creating PermissionGrant with both scopes for the same target
    from apps.access.serializers import PermissionGrantSerializer
    user = User.objects.create_user(email="grant-fail@example.com", password="strong-password-123")
    book = Book.objects.create(title="Grant Fail Book", state="ready", review_state="approved")

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.READ_ONCE)

    grant_serializer = PermissionGrantSerializer(
        data={
            "user": user.id,
            "book": book.id,
            "scope": "read:durable"
        }
    )
    assert grant_serializer.is_valid() is False
    assert "non_field_errors" in grant_serializer.errors or "detail" in grant_serializer.errors or any("Read Once and Durable Read" in err for err in grant_serializer.errors.values())

