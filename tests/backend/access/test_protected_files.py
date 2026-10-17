from pathlib import Path
from urllib.parse import quote

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.access.protected_files import protected_file_response
from apps.catalog.models import UserBook
from django.http import Http404
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_authorized_chapter_uses_internal_redirect_and_preserves_sandbox(
    reader, settings
):
    settings.PROTECTED_FILES_USE_NGINX = True
    client, _, book, _, publication = reader
    launched = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    path = launched["resource_base"] + "OEBPS/chapter-1.xhtml"
    response = client.get(path)
    assert (
        response.status_code == 200
        and not response.streaming
        and response.content == b""
    )
    assert (
        response["X-Accel-Redirect"]
        == f"/_protected/protected/reader/{publication.storage_reference}/OEBPS/chapter-1.xhtml"
    )
    assert int(response["Content-Length"]) > 0
    assert "sandbox allow-same-origin" in response["Content-Security-Policy"]
    assert response["Cache-Control"] == "private, no-store"
    assert APIClient().get(path).status_code == 403


def test_revoked_access_never_reaches_the_internal_redirect(reader, settings):
    settings.PROTECTED_FILES_USE_NGINX = True
    client, user, book, _, _ = reader
    UserBook.objects.filter(user=user, book=book).delete()
    grant = PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_DURABLE
    )
    data = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    grant.is_active = False
    grant.save()
    response = client.get(data["resource_base"] + "OEBPS/chapter-1.xhtml")
    assert response.status_code == 403 and "X-Accel-Redirect" not in response


def test_download_redirect_has_a_safe_unicode_filename(reader, settings):
    settings.PROTECTED_FILES_USE_NGINX = True
    client, _, book, asset, _ = reader
    relative = "protected/generated/বাংলা বই.epub"
    target = Path(settings.MEDIA_ROOT) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(Path(asset.legacy_path).read_bytes())
    asset.file.name = relative
    asset.save()
    response = client.get(f"/api/v1/reading/books/{book.slug}/download/")
    assert response.status_code == 200
    assert response["X-Accel-Redirect"] == "/_protected/" + quote(relative)
    assert response["Content-Type"] == "application/epub+zip"
    assert response["Content-Disposition"].startswith("attachment; filename*=utf-8''")
    assert response["Cache-Control"] == "private, no-store"


def test_accelerated_download_rejects_a_file_outside_shared_storage(reader, settings):
    settings.PROTECTED_FILES_USE_NGINX = True
    client, _, book, _, _ = reader
    response = client.get(f"/api/v1/reading/books/{book.slug}/download/")
    assert response.status_code == 404 and "X-Accel-Redirect" not in response


@pytest.mark.parametrize("path", [None, "", "missing.epub"])
def test_invalid_or_missing_accelerated_paths_are_not_served(settings, path):
    settings.PROTECTED_FILES_USE_NGINX = True
    with pytest.raises(Http404):
        protected_file_response(path)


def test_symlink_escape_is_not_served(settings, tmp_path):
    settings.PROTECTED_FILES_USE_NGINX = True
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir()
    outside = tmp_path / "private.epub"
    outside.write_bytes(b"private")
    link = settings.MEDIA_ROOT / "escape.epub"
    link.symlink_to(outside)
    with pytest.raises(Http404):
        protected_file_response(link)


def test_development_streaming_remains_available(settings, tmp_path):
    settings.PROTECTED_FILES_USE_NGINX = False
    path = tmp_path / "chapter.xhtml"
    path.write_bytes(b"<p>chapter</p>")
    response = protected_file_response(path, "application/xhtml+xml")
    try:
        assert b"".join(response.streaming_content) == b"<p>chapter</p>"
        assert "X-Accel-Redirect" not in response
    finally:
        response.close()
