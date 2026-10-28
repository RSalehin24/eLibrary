import pytest
from apps.catalog.models import Book, BookGroup

pytestmark = pytest.mark.django_db


def test_edition_feed_exposes_only_public_siblings_and_binds_its_cursor(client):
    group = BookGroup.objects.create(canonical_title="একই কাজ")
    books = [
        Book.objects.create(title=f"সংস্করণ {index}", group=group, state="published")
        for index in range(4)
    ]
    Book.objects.create(title="গোপন সংস্করণ", group=group)
    path = f"/api/v1/catalog/books/{books[0].slug}/editions/"
    first = client.get(path, {"limit": 1}).json()
    assert len(first["entries"]) == 1 and first["has_more"]
    assert first["entries"][0]["id"] != str(books[0].pk)
    second = client.get(path, {"limit": 1, "cursor": first["next_cursor"]}).json()
    assert second["entries"][0]["id"] != first["entries"][0]["id"]
    assert (
        client.get(
            f"/api/v1/catalog/books/{books[1].slug}/editions/",
            {"cursor": first["next_cursor"]},
        ).status_code
        == 400
    )
    assert len(client.get(path).json()["entries"]) == 3


def test_ungrouped_books_do_not_match_other_ungrouped_books(client):
    book = Book.objects.create(title="একক বই", state="published")
    Book.objects.create(title="অন্য একক বই", state="published")
    assert (
        client.get(f"/api/v1/catalog/books/{book.slug}/editions/").json()["entries"]
        == []
    )
