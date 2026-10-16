import pytest
from apps.access.models import ReadingSession
from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def library():
    owner = User.objects.create_user(
        email="owner@library.test", password="test-password"
    )
    stranger = User.objects.create_user(
        email="stranger@library.test", password="test-password"
    )
    book = Book.objects.create(title="ব্যক্তিগত বই", main_content_html="private body")
    UserBook.objects.create(user=owner, book=book)
    ReadingSession.objects.create(
        user=owner, book=book, progress_percent=42, last_location="chapter-2"
    )
    client = APIClient()
    client.force_authenticate(owner)
    return client, stranger, book


def test_library_requires_authentication():
    assert APIClient().get("/api/v1/me/books/").status_code == 403


def test_library_returns_only_owned_metadata_and_own_progress(
    library, django_assert_num_queries
):
    client, stranger, book = library
    UserBook.objects.create(
        user=stranger, book=Book.objects.create(title="অন্য পাঠকের বই")
    )
    ReadingSession.objects.create(user=stranger, book=book, progress_percent=90)
    with django_assert_num_queries(4):
        response = client.get("/api/v1/me/books/")
    entry = response.json()["entries"][0]
    assert entry["id"] == str(book.pk)
    assert entry["progress_percent"] == 42
    assert entry["last_location"] == "chapter-2"
    assert "main_content_html" not in entry
    assert response["Cache-Control"] == "private, no-store"


def test_private_detail_does_not_expose_another_owners_record(library):
    client, stranger, book = library
    path = f"/api/v1/me/books/{book.slug}/"
    assert client.get(path).status_code == 200
    client.force_authenticate(stranger)
    assert client.get(path).status_code == 404
    assert APIClient().get(f"/api/v1/catalog/books/{book.slug}/").status_code == 404


def test_library_cursor_is_bound_to_account(library):
    client, stranger, book = library
    owner = UserBook.objects.get(book=book).user
    UserBook.objects.create(user=owner, book=Book.objects.create(title="দ্বিতীয় বই"))
    cursor = client.get("/api/v1/me/books/?limit=1").json()["next_cursor"]
    client.force_authenticate(stranger)
    response = client.get("/api/v1/me/books/", {"limit": 1, "cursor": cursor})
    assert response.status_code == 400
    assert "cursor" in response.json()["field_errors"]
