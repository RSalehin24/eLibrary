import pytest
from apps.catalog.models import Book, BookContributor, Contributor
from django.utils import timezone

pytestmark = pytest.mark.django_db


def eligible_book(**fields):
    values = {
        "title": "সূচিভুক্ত বই",
        "state": "published",
        "review_state": "approved",
        "indexing_eligible": True,
        "editorial_reviewed_at": timezone.now(),
        "editorial_description": "পর্যালোচিত পরিচিতি",
    }
    return Book.objects.create(**(values | fields))


def test_sitemap_contains_only_canonical_indexable_public_records(client):
    book = eligible_book()
    old_slug = book.slug
    book.title = "নতুন পরিচিতি"
    book.save()
    excluded = [eligible_book() for _ in range(4)]
    excluded[0].indexing_eligible = False
    excluded[1].editorial_reviewed_at = None
    excluded[2].editorial_description = " \n\t "
    excluded[3].state = "draft"
    for entry in excluded:
        entry.save()
    response = client.get("/api/v1/catalog/sitemaps/books/1/")
    assert response.status_code == 200
    assert [entry["slug"] for entry in response.json()] == [book.slug]
    assert old_slug not in str(response.json())
    assert set(response.json()[0]) == {"slug", "updated_at"}
    book.soft_delete()
    assert client.get("/api/v1/catalog/sitemaps/books/1/").status_code == 404


def test_entity_sitemap_requires_reviewed_introduction_and_public_books(client):
    author = Contributor.objects.create(
        name="পর্যালোচিত লেখক",
        editorial_description="যাচাইকৃত জীবনী",
        indexing_eligible=True,
        editorial_reviewed_at=timezone.now(),
    )
    path = "/api/v1/catalog/sitemaps/contributors/1/"
    assert client.get(path).status_code == 404
    book = eligible_book()
    BookContributor.objects.create(book=book, contributor=author)
    assert client.get(path).json()[0]["slug"] == author.slug
    index = client.get("/api/v1/catalog/sitemaps/").json()
    assert {entry["kind"]: entry["pages"] for entry in index} == {
        "books": 1,
        "contributors": 1,
        "categories": 0,
        "series": 0,
        "collections": 0,
    }


def test_sitemap_children_are_bounded_and_pages_are_disjoint(client):
    books = [eligible_book(title=f"সূচিভুক্ত বই {number}") for number in range(1001)]
    first = client.get("/api/v1/catalog/sitemaps/books/1/").json()
    second = client.get("/api/v1/catalog/sitemaps/books/2/").json()
    assert len(first) == 1000
    assert len(second) == 1
    assert {entry["slug"] for entry in first + second} == {book.slug for book in books}
    assert client.get("/api/v1/catalog/sitemaps/books/3/").status_code == 404
    assert client.get("/api/v1/catalog/sitemaps/books/0/").status_code == 404
    assert client.get("/api/v1/catalog/sitemaps/private/1/").status_code == 404
