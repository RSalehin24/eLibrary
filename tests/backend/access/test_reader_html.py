import pytest
from apps.access.models import BookOpeningRecord, PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import GeneratedAsset, UserBook
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def html_reader(reader):
    client, user, book, _, _ = reader
    asset = GeneratedAsset(book=book, asset_type="html", status="ready")
    asset.file.save("reader.html", ContentFile(b"<!doctype html><h1>Book text</h1>"))
    return client, user, book, asset


def preview_url(book):
    return reverse("api_v1:reader-html", kwargs={"slug": book.slug})


def access(client, book):
    return client.get(f"/api/v1/reading/books/{book.slug}/access/").json()


def test_owned_book_opens_actual_inline_html_privately(html_reader, settings):
    settings.PROTECTED_FILES_USE_NGINX = False
    client, _, book, _ = html_reader
    assert access(client, book)["html_url"] == preview_url(book)
    response = client.get(preview_url(book))
    assert response.status_code == 200
    assert b"Book text" in b"".join(response.streaming_content)
    assert response["Content-Type"].startswith("text/html")
    assert response["Content-Disposition"].startswith("inline;")
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Robots-Tag"] == "noindex"
    assert response["Referrer-Policy"] == "no-referrer"
    assert response["X-Content-Type-Options"] == "nosniff"
    policy = response["Content-Security-Policy"]
    assert "sandbox" in policy and "default-src 'none'" in policy
    assert "allow-scripts" not in policy and "allow-same-origin" not in policy


@pytest.mark.parametrize(
    "scope", [None, PermissionScope.DOWNLOAD_FILE, PermissionScope.PROCESSING_MANAGE]
)
def test_file_and_processing_scopes_do_not_grant_html_preview(html_reader, scope):
    client, user, book, _ = html_reader
    UserBook.objects.filter(user=user, book=book).delete()
    if scope:
        PermissionGrant.objects.create(user=user, book=book, scope=scope)
    assert access(client, book)["html_url"] is None
    assert client.get(preview_url(book)).status_code == 403
    assert APIClient().get(preview_url(book)).status_code == 403


def test_html_obeys_existing_read_once_consumption(html_reader):
    client, user, book, _ = html_reader
    UserBook.objects.filter(user=user, book=book).delete()
    for scope in [PermissionScope.PREVIEW_HTML, PermissionScope.READ_ONCE]:
        PermissionGrant.objects.create(user=user, book=book, scope=scope)
    assert access(client, book)["html_url"] == preview_url(book)
    assert not BookOpeningRecord.objects.filter(user=user, book=book).exists()
    response = client.get(preview_url(book))
    assert response.status_code == 200
    assert b"".join(response.streaming_content)
    assert BookOpeningRecord.objects.filter(user=user, book=book).count() == 1
    assert access(client, book)["html_url"] is None
    assert client.get(preview_url(book)).status_code == 403


@pytest.mark.parametrize("condition", ["missing", "failed", "removed"])
def test_unavailable_html_never_consumes_an_opening(html_reader, condition):
    client, user, book, asset = html_reader
    UserBook.objects.filter(user=user, book=book).delete()
    for scope in [PermissionScope.PREVIEW_HTML, PermissionScope.READ_ONCE]:
        PermissionGrant.objects.create(user=user, book=book, scope=scope)
    if condition == "missing":
        asset.file = ""
    elif condition == "failed":
        asset.status = "failed"
    else:
        book.deleted_at = timezone.now()
        book.save()
    asset.save()
    assert client.get(preview_url(book)).status_code == 404
    assert not BookOpeningRecord.objects.filter(user=user, book=book).exists()


def test_html_nginx_response_uses_inline_protected_file(html_reader, settings):
    settings.PROTECTED_FILES_USE_NGINX = True
    client, _, book, _ = html_reader
    response = client.get(preview_url(book))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/html"
    assert response["Content-Disposition"].startswith("inline;")
    assert response["X-Accel-Redirect"].startswith("/_protected/")


def test_disabled_account_cannot_open_html(html_reader):
    client, user, book, _ = html_reader
    user.is_active = False
    user.save()
    assert client.get(preview_url(book)).status_code == 403
    stranger = User.objects.create_user(email="no-html@example.test")
    client.force_authenticate(stranger)
    assert client.get(preview_url(book)).status_code == 403
