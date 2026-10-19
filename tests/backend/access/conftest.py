import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from rest_framework.test import APIClient

from .reader_fixtures import prepared_asset


@pytest.fixture
def reader(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    user = User.objects.create_user(email="reader-api@library.test")
    book = Book.objects.create(title="পাঠকের বই")
    UserBook.objects.create(user=user, book=book)
    client = APIClient()
    client.force_authenticate(user)
    asset, publication = prepared_asset(book, tmp_path)
    return client, user, book, asset, publication


@pytest.fixture
def annotation_session(reader):
    client, _, book, _, _ = reader
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    return f"/api/v1/reading/sessions/{session['id']}"
