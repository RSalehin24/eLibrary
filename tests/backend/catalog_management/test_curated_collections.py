import pytest
from apps.catalog.models import Book, CollectionBook, CuratedCollection
from django.db import IntegrityError, transaction
from rest_framework.fields import DateTimeField

pytestmark = pytest.mark.django_db


def collection_with_books():
    collection = CuratedCollection.objects.create(
        name="নির্বাচিত বাংলা গল্প",
        state="published",
        editorial_description="গল্প বাছাইয়ের পর্যালোচিত সম্পাদকীয় পরিচিতি।",
        indexing_eligible=True,
    )
    earlier = Book.objects.create(title="প্রথম নির্বাচিত বই", state="published")
    later = Book.objects.create(title="দ্বিতীয় নির্বাচিত বই", state="published")
    private = Book.objects.create(title="গোপন খসড়া")
    CollectionBook.objects.create(collection=collection, book=earlier, position=5)
    CollectionBook.objects.create(collection=collection, book=later, position=20)
    CollectionBook.objects.create(collection=collection, book=private, position=0)
    return collection, earlier, later


def test_collection_feed_is_lightweight_and_detail_is_reviewed(
    client, django_assert_num_queries
):
    collection, _, _ = collection_with_books()
    with django_assert_num_queries(1):
        response = client.get("/api/v1/catalog/collections/")
    assert response.json()["entries"] == [
        {
            "id": str(collection.id),
            "name": collection.name,
            "slug": collection.slug,
            "book_count": 2,
            "catalog_code": None,
            "created_at": DateTimeField().to_representation(collection.created_at),
        }
    ]
    detail = client.get(
        f"/api/v1/catalog/entities/collections/{collection.slug}/"
    ).json()
    assert detail["editorial_description"] == collection.editorial_description
    assert detail["indexable"] is True
    assert "books" not in detail


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "draft"},
        {"state": "archived"},
        {"editorial_description": " \n "},
    ],
)
def test_unpublished_or_incomplete_collections_are_not_public(client, changes):
    collection, _, _ = collection_with_books()
    for field, value in changes.items():
        setattr(collection, field, value)
    collection.save()
    assert not client.get("/api/v1/catalog/collections/").json()["entries"]
    assert (
        client.get(
            f"/api/v1/catalog/entities/collections/{collection.slug}/"
        ).status_code
        == 404
    )
    assert not client.get(
        "/api/v1/catalog/books/", {"collection": collection.slug}
    ).json()["entries"]


def test_collection_books_follow_editorial_order_and_never_include_drafts(client):
    collection, first, second = collection_with_books()
    path = "/api/v1/catalog/books/"
    initial = client.get(path, {"collection": collection.slug, "limit": 1}).json()
    assert initial["entries"][0]["id"] == str(first.id)
    following = client.get(
        path,
        {"collection": collection.slug, "limit": 1, "cursor": initial["next_cursor"]},
    ).json()
    assert [entry["id"] for entry in following["entries"]] == [str(second.id)]
    assert following["has_more"] is False
    assert client.get(path, {"cursor": initial["next_cursor"]}).status_code == 400


def test_membership_is_unique_in_the_database():
    collection, book, _ = collection_with_books()
    with pytest.raises(IntegrityError), transaction.atomic():
        CollectionBook.objects.create(collection=collection, book=book)


def test_renamed_collections_resolve_to_canonical_slugs(client):
    collection, _, _ = collection_with_books()
    previous_slug = collection.slug
    collection.name = "নতুন নির্বাচিত বাংলা গল্প"
    collection.save()
    response = client.get(f"/api/v1/catalog/entities/collections/{previous_slug}/")
    assert response.json()["slug"] == collection.slug
    assert (
        client.get("/api/v1/catalog/sitemaps/collections/1/").json()[0]["slug"]
        == collection.slug
    )
