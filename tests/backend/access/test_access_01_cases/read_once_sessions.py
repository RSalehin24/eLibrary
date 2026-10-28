from pathlib import Path

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)


@pytest.mark.django_db
def test_read_once_permission_blocks_subsequent_launches(tmp_path, client):
    user = User.objects.create_user(
        email="once-reader@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="Read Once Book", state="ready")
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

    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    client.force_login(user)

    # First launch should succeed
    response = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response.status_code == 200

    # Second launch should fail
    response2 = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response2.status_code == 403


@pytest.mark.django_db
def test_read_once_permission_blocks_html_previews(tmp_path, client):
    user = User.objects.create_user(
        email="once-html-reader@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="Read Once HTML Book", state="ready")
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

    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.PREVIEW_HTML
    )
    client.force_login(user)

    # First HTML download should succeed
    response = client.get(f"/api/access/books/{book.slug}/download/html/")
    assert response.status_code == 200

    # Second HTML download should fail
    response2 = client.get(f"/api/access/books/{book.slug}/download/html/")
    assert response2.status_code == 403


@pytest.mark.django_db
def test_read_once_html_preview_blocks_reader_launch(tmp_path, client):
    user = User.objects.create_user(
        email="once-cross-reader@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="Cross Read Book", state="ready")
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

    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.PREVIEW_HTML
    )
    client.force_login(user)

    # First download HTML preview
    response = client.get(f"/api/access/books/{book.slug}/download/html/")
    assert response.status_code == 200

    # Reader launch is now blocked
    response2 = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert response2.status_code == 403


@pytest.mark.django_db
def test_read_once_without_preview_html_permission_cannot_view_html(tmp_path, client):
    user = User.objects.create_user(
        email="once-no-html@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="No HTML Book", state="ready")
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

    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
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

    user = User.objects.create_user(
        email="grant-fail@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="Grant Fail Book", state="ready")

    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )

    grant_serializer = PermissionGrantSerializer(
        data={"user": user.id, "book": book.id, "scope": "read:durable"}
    )
    assert grant_serializer.is_valid() is False
    assert (
        "non_field_errors" in grant_serializer.errors
        or "detail" in grant_serializer.errors
        or any(
            "Read Once and Durable Read" in err
            for err in grant_serializer.errors.values()
        )
    )
