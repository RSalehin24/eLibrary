import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, BookCategory, Category, SavedBook

pytestmark = pytest.mark.django_db


def test_public_total_pages_respect_filters_and_exclude_hidden_books(client):
    category = Category.objects.create(name="Pagination category")
    for index in range(5):
        book = Book.objects.create(title=f"Page count {index}", state="published")
        if index < 3:
            BookCategory.objects.create(book=book, category=category)
    Book.objects.create(title="Hidden book", state="draft")
    response = client.get(
        "/api/v1/catalog/books/", {"category": category.slug, "page": 2, "limit": 2}
    )
    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "page": 2,
        "limit": 2,
        "total_count": 3,
        "page_count": 2,
    }
    assert len(response.json()["entries"]) == 1


def test_personal_page_counts_cannot_include_another_accounts_saved_books(client):
    actor = User.objects.create_user(email="pagination-reader@example.test")
    other = User.objects.create_user(email="other-pagination@example.test")
    for index in range(4):
        book = Book.objects.create(title=f"Personal page {index}", state="published")
        SavedBook.objects.create(user=actor if index < 3 else other, book=book)
    client.force_login(actor)
    payload = client.get(
        "/api/v1/me/books/", {"view": "saved", "limit": 2, "page": 2}
    ).json()
    assert payload["pagination"] == {
        "page": 2,
        "limit": 2,
        "total_count": 3,
        "page_count": 2,
    }
    assert len(payload["entries"]) == 1 and not payload["has_more"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/catalog/books/",
        "/api/v1/catalog/entities/contributors/",
        "/api/v1/catalog/collections/",
    ],
)
def test_empty_collections_have_one_empty_page_without_fake_next_pages(client, path):
    response = client.get(path, {"limit": 2})
    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "page": 1,
        "limit": 2,
        "total_count": 0,
        "page_count": 1,
    }
    assert not response.json()["has_more"]
