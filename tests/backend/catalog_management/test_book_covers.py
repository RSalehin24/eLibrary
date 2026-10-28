from io import BytesIO

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset, UserBook
from django.core.files.base import ContentFile
from PIL import Image
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def cover(book):
    data = BytesIO()
    Image.new("RGB", (20, 30), "green").save(data, format="JPEG")
    asset = GeneratedAsset(
        book=book, asset_type="cover", status="ready", content_type="image/jpeg"
    )
    asset.file.save("cover.jpg", ContentFile(data.getvalue()))
    return asset


def url(book):
    return f"/api/v1/catalog/books/{book.slug}/cover/"


def test_published_cover_is_real_image_and_metadata_has_its_url(settings):
    settings.PROTECTED_FILES_USE_NGINX = False
    book = Book.objects.create(title="Cover book", state="published")
    cover(book)
    client = APIClient()
    response = client.get(url(book))
    assert response.status_code == 200
    assert b"".join(response.streaming_content).startswith(b"\xff\xd8")
    assert response["Content-Type"] == "image/jpeg"
    assert response["Content-Disposition"] == "inline"
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Content-Type-Options"] == "nosniff"
    entry = client.get("/api/v1/catalog/books/").json()["entries"][0]
    assert entry["cover_url"].startswith(url(book) + "?revision=")


def test_private_cover_requires_existing_reader_permission():
    book = Book.objects.create(title="Private cover")
    cover(book)
    client = APIClient()
    assert client.get(url(book)).status_code == 403
    actor = User.objects.create_user(email="cover-owner@example.test")
    client.force_authenticate(actor)
    assert client.get(url(book)).status_code == 403
    UserBook.objects.create(book=book, user=actor)
    response = client.get(url(book))
    assert response.status_code == 200
    assert b"".join(response.streaming_content)
    actor.is_active = False
    actor.save()
    assert client.get(url(book)).status_code == 403


def test_absent_and_non_image_assets_are_not_served():
    book = Book.objects.create(title="Missing cover", state="published")
    client = APIClient()
    assert client.get(url(book)).status_code == 404
    assert (
        client.get("/api/v1/catalog/books/").json()["entries"][0]["cover_url"] is None
    )
    asset = cover(book)
    asset.content_type = "text/html"
    asset.save()
    assert client.get(url(book)).status_code == 404
    book.soft_delete()
    assert client.get(url(book)).status_code == 404


def test_cover_uses_nginx_protected_delivery(settings):
    settings.PROTECTED_FILES_USE_NGINX = True
    book = Book.objects.create(title="Nginx cover", state="published")
    cover(book)
    response = APIClient().get(url(book))
    assert response.status_code == 200
    assert response["X-Accel-Redirect"].startswith("/_protected/")
    assert response["Content-Type"] == "image/jpeg"
