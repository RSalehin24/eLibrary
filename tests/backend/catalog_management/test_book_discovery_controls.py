import pytest
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    CollectionBook,
    Contributor,
    CuratedCollection,
    SavedBook,
    Series,
)
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_default_my_books_includes_added_books_without_transferring_access():
    actor = User.objects.create_user(email="personal-library-add@example.test")
    other = User.objects.create_user(email="personal-library-other@example.test")
    book = Book.objects.create(title="পাঠকের নিজের তালিকা", state="published")
    private = Book.objects.create(title="অন্যের খসড়া")
    SavedBook.objects.create(user=other, book=private)
    client = APIClient()
    client.force_authenticate(actor)
    path = f"/api/v1/me/books/{book.slug}/saved/"
    assert client.put(path, {"saved": True}, format="json").status_code == 200
    feed = client.get("/api/v1/me/books/").json()
    assert [entry["id"] for entry in feed["entries"]] == [str(book.pk)]
    assert (
        client.put(
            f"/api/v1/me/books/{private.slug}/saved/", {"saved": True}, format="json"
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/reading/books/{book.slug}/access/").json()["can_read"]
        is False
    )
    assert client.put(path, {"saved": False}, format="json").status_code == 200
    assert client.get("/api/v1/me/books/").json()["entries"] == []


@pytest.mark.parametrize("kind", ["contributor", "category", "series", "collection"])
def test_managed_entity_book_links_include_related_drafts(kind):
    actor = User.objects.create_user(email="entity-books@example.test", is_staff=True)
    book = Book.objects.create(title="সম্পর্কিত খসড়া")
    Book.objects.create(title="অন্য খসড়া")
    models = {
        "contributor": Contributor,
        "category": Category,
        "series": Series,
        "collection": CuratedCollection,
    }
    links = {
        "contributor": BookContributor,
        "category": BookCategory,
        "series": BookSeries,
        "collection": CollectionBook,
    }
    entity = models[kind].objects.create(name="বইয়ের সম্পর্ক")
    links[kind].objects.create(book=book, **{kind: entity})
    client = APIClient()
    client.force_authenticate(actor)
    response = client.get("/api/v1/manage/books/", {kind: entity.slug})
    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()["entries"]] == [str(book.pk)]
