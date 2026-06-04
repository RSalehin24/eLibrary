from pathlib import Path
from urllib.parse import quote

import pytest
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile

from apps.access.models import PermissionGrant, PermissionScope, PreviewAccessSession
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSource,
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
def test_reader_state_requires_reader_access(tmp_path, client):
    user = User.objects.create_user(email="reader-state@example.com", password="strong-password-123")
    book = Book.objects.create(title="Reader State Book", state="ready", review_state="approved")
    client.force_login(user)

    denied_session = client.get(f"/api/access/books/{book.slug}/reading-session/")
    denied_bookmarks = client.get(f"/api/access/books/{book.slug}/bookmarks/")
    assert denied_session.status_code == 403
    assert denied_bookmarks.status_code == 403

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.READ_DURABLE)

    allowed_session = client.post(
        f"/api/access/books/{book.slug}/reading-session/",
        data={"last_location": "chapter-1", "progress_percent": 12},
    )
    assert allowed_session.status_code == 200

    bookmark = client.post(
        f"/api/access/books/{book.slug}/bookmarks/",
        data={"location": "chapter-1", "label": "Start", "note": "Important"},
    )
    assert bookmark.status_code == 201


@pytest.mark.django_db
def test_reader_html_preview_inlines_stale_relative_cover_references(tmp_path, client):
    book = Book.objects.create(title="HTML Preview Book", state="ready", review_state="approved")
    html_path = Path(tmp_path) / "book.html"
    cover_path = Path(tmp_path) / "book_cover.jpg"
    html_path.write_text(
        "<!DOCTYPE html><html><body><img src='book_image.hpg' alt='Book Cover' class='cover-image'></body></html>",
        encoding="utf-8",
    )
    cover_path.write_bytes(b"cover-bytes")

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
        asset_type=GeneratedAssetType.COVER,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(cover_path),
        content_type="image/jpeg",
        file_size=cover_path.stat().st_size,
    )
    session = PreviewAccessSession.objects.create(book=book)

    response = client.get(f"/api/access/reader/{session.token}/html/")

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "data:image/jpeg;base64," in body
    assert "book_image.hpg" not in body


@pytest.mark.django_db
def test_reader_html_preview_promotes_leading_front_matter_from_main_content(tmp_path, client):
    book = Book.objects.create(title="HTML Front Matter Book", state="ready", review_state="approved")
    html_path = Path(tmp_path) / "book.html"
    html_path.write_text(
        """
        <!DOCTYPE html>
        <html>
          <body>
            <div class="container">
              <div class="main-content">
                <h2 class="wp-block-heading">ম্যালিস – কিয়েগো হিগাশিনো</h2>
                <p><strong>ম্যালিস – কিয়েগো হিগাশিনো</strong><br/>অনুবাদ: সালমান হক, ইশরাক অর্ণব</p>
                <p>প্রথম প্রকাশ: মার্চ ২০২৩</p>
                <p><strong>ভূমিকা</strong></p>
                <p>এটাই মূল কনটেন্ট।</p>
              </div>
            </div>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )
    session = PreviewAccessSession.objects.create(book=book)

    response = client.get(f"/api/access/reader/{session.token}/html/")

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "book-info-section" in body
    assert "অনুবাদ: সালমান হক, ইশরাক অর্ণব" in body
    assert "প্রথম প্রকাশ: মার্চ ২০২৩" in body
    main_content_fragment = body.split('<div class="main-content">', 1)[1]
    assert "অনুবাদ: সালমান হক, ইশরাক অর্ণব" not in main_content_fragment
    assert "প্রথম প্রকাশ: মার্চ ২০২৩" not in main_content_fragment


@pytest.mark.django_db
def test_only_superadmin_can_manage_grants(client):
    superadmin = User.objects.create_superuser(email="superadmin@example.com", password="strong-password-123")
    manager = User.objects.create_user(email="grant-manager@example.com", password="strong-password-123")
    target = User.objects.create_user(email="target@example.com", password="strong-password-123")
    book = Book.objects.create(title="Grant Scope Book", state="ready", review_state="approved")
    client.force_login(manager)

    denied = client.get("/api/access/references/")
    assert denied.status_code == 403

    client.force_login(superadmin)
    references = client.get("/api/access/references/")
    assert references.status_code == 200
    reference_payload = references.json()
    assert "account_scopes" in reference_payload
    assert "scoped_scopes" in reference_payload
    assert "admin:full_control" not in {scope["value"] for scope in reference_payload["account_scopes"]}
    assert "access:manage" not in {scope["value"] for scope in reference_payload["scoped_scopes"]}

    created = client.post(
        "/api/access/grants/",
        data={
            "user": str(target.id),
            "book": str(book.id),
            "scope": PermissionScope.DOWNLOAD_FILE,
            "notes": "Scoped by grant manager",
        },
    )
    assert created.status_code == 201

    deleted = client.delete(f"/api/access/grants/{created.json()['id']}/")
    assert deleted.status_code == 204


@pytest.mark.django_db
def test_superadmin_cannot_create_or_delete_own_scoped_access_grants(client):
    superadmin = User.objects.create_superuser(email="self-grant-block@example.com", password="strong-password-123")
    other_user = User.objects.create_user(email="self-grant-other@example.com", password="strong-password-123")
    book = Book.objects.create(title="Self Grant Scope Book", state="ready", review_state="approved")
    client.force_login(superadmin)

    create_self = client.post(
        "/api/access/grants/",
        data={
            "user": str(superadmin.id),
            "book": str(book.id),
            "scope": PermissionScope.DOWNLOAD_FILE,
            "notes": "Should be blocked",
        },
    )
    assert create_self.status_code == 403

    created_other = client.post(
        "/api/access/grants/",
        data={
            "user": str(other_user.id),
            "book": str(book.id),
            "scope": PermissionScope.DOWNLOAD_FILE,
            "notes": "Allowed",
        },
    )
    assert created_other.status_code == 201

    grant_id = created_other.json()["id"]
    grant = PermissionGrant.objects.get(pk=grant_id)
    grant.user = superadmin
    grant.save(update_fields=["user", "updated_at"])

    delete_self = client.delete(f"/api/access/grants/{grant_id}/")
    assert delete_self.status_code == 403


@pytest.mark.django_db
def test_category_and_writer_scoped_permissions_apply_to_matching_books():
    user = User.objects.create_user(email="scoped@example.com", password="strong-password-123")
    category = Category.objects.create(name="Thriller")
    writer = Contributor.objects.create(name="Writer One")
    category_book = Book.objects.create(title="Category Book", state="ready", review_state="approved")
    writer_book = Book.objects.create(title="Writer Book", state="ready", review_state="approved")
    other_book = Book.objects.create(title="Other Book", state="ready", review_state="approved")

    BookCategory.objects.create(book=category_book, category=category)
    BookContributor.objects.create(book=writer_book, contributor=writer, role=ContributorRole.AUTHOR)

    PermissionGrant.objects.create(user=user, category=category, scope=PermissionScope.DOWNLOAD_FILE)
    PermissionGrant.objects.create(user=user, contributor=writer, scope=PermissionScope.READ_DURABLE)

    assert user_has_scope(user, [PermissionScope.DOWNLOAD_FILE], book=category_book) is True
    assert user_has_scope(user, [PermissionScope.DOWNLOAD_FILE], book=other_book) is False
    assert user_has_scope(user, [PermissionScope.READ_DURABLE], book=writer_book) is True
    assert user_has_scope(user, [PermissionScope.READ_DURABLE], book=category_book) is False


@pytest.mark.django_db
def test_catalog_endpoints_require_authentication(client):
    book = Book.objects.create(title="Private Catalog Book", state="ready", review_state="approved")

    list_response = client.get("/api/catalog/books/")
    detail_response = client.get(f"/api/catalog/books/{book.slug}/")

    assert list_response.status_code == 403
    assert detail_response.status_code == 403


@pytest.mark.django_db
def test_book_source_visibility_and_uniqueness(client):
    from django.db.utils import IntegrityError
    # 1. Test uniqueness of BookSource
    book = Book.objects.create(title="Source Book", state="ready", review_state="approved")
    source1 = BookSource.objects.create(book=book, source_url="https://example.com/1", normalized_source_url="https://example.com/1")
    from django.db import transaction
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            BookSource.objects.create(book=book, source_url="https://example.com/2", normalized_source_url="https://example.com/2")

    # 2. Setup user and test visibility
    user = User.objects.create_user(email="reader@example.com", password="strong-password-123")
    client.force_login(user)

    # Without permission, source_urls and source_records should be empty
    response = client.get(f"/api/catalog/books/{book.slug}/")
    assert response.status_code == 200
    data = response.json()
    assert data["source_urls"] == []
    assert data["source_records"] == []

    # Grant VIEW_SOURCE_RECORDS permission
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.VIEW_SOURCE_RECORDS)
    
    # With permission, they should be visible
    response = client.get(f"/api/catalog/books/{book.slug}/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["source_urls"]) == 1
    assert data["source_urls"][0] == "https://example.com/1"
    assert len(data["source_records"]) == 1
    assert data["source_records"][0]["url"] == "https://example.com/1"

    # Super admin should see it automatically
    superadmin = User.objects.create_superuser(email="super@example.com", password="strong-password-123")
    client.force_login(superadmin)
    response = client.get(f"/api/catalog/books/{book.slug}/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["source_urls"]) == 1

