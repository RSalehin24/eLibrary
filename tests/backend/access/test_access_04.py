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
    Category,
    Contributor,
    ContributorRole,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.common.epub_utils import build_simple_epub
from apps.common.permissions import user_has_scope
from apps.ingestion.models import BookSubmission, ResolutionStatus, SubmissionStatus
from apps.access.views import normalize_preview_book_sections


def assert_content_disposition_filename(header_value, expected_filename):
    assert (
        f'filename="{expected_filename}"' in header_value
        or f"filename*=utf-8''{quote(expected_filename)}" in header_value
    )


@pytest.mark.django_db
def test_reader_token_state_and_bookmark_endpoints_work(tmp_path, client):
    user = User.objects.create_user(email="token-reader@example.com", password="strong-password-123")
    book = Book.objects.create(title="Token Reader Book", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "token-reader.epub"
    epub_path.write_bytes(build_simple_epub("Token Reader Book"))

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.PREVIEW_HTML)
    client.force_login(user)
    launch = client.post(f"/api/access/books/{book.slug}/reader-launch/")
    assert launch.status_code == 200

    manifest_path = launch.json()["manifest_url"].replace("http://testserver", "")
    manifest = client.get(manifest_path)
    assert manifest.status_code == 200
    payload = manifest.json()

    container_response = client.get(
        f"{payload['epub_download_url'].replace('http://testserver', '')}META-INF/container.xml"
    )
    assert container_response.status_code == 200
    assert b"OEBPS/content.opf" in container_response.content

    chapter_response = client.get(
        f"{payload['epub_download_url'].replace('http://testserver', '')}OEBPS/text/chapter-1.xhtml"
    )
    assert chapter_response.status_code == 200
    assert b"Seeded EPUB chapter one for reader coverage." in chapter_response.content

    session_get = client.get(payload["reading_session_url"].replace("http://testserver", ""))
    assert session_get.status_code == 200

    session_post = client.post(
        payload["reading_session_url"].replace("http://testserver", ""),
        data={"last_location": "chapter-2", "progress_percent": 47},
    )
    assert session_post.status_code == 200
    assert session_post.json()["last_location"] == "chapter-2"

    bookmark_post = client.post(
        payload["bookmarks_url"].replace("http://testserver", ""),
        data={"location": "chapter-2", "label": "Keep", "note": "Token bookmark"},
    )
    assert bookmark_post.status_code == 201

    bookmark_list = client.get(payload["bookmarks_url"].replace("http://testserver", ""))
    assert bookmark_list.status_code == 200
    assert len(bookmark_list.json()) == 1

    delete_url = f"/api/access/reader/{manifest_path.split('/reader/')[1].split('/manifest/')[0]}/bookmarks/{bookmark_post.json()['id']}/"
    deleted = client.delete(delete_url)
    assert deleted.status_code == 204
