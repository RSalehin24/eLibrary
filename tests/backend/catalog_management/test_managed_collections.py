from uuid import uuid4

import pytest
from apps.catalog.models import Book, CuratedCollection
from apps.common.models import AuditLog

from .entity_fixtures import (
    create_entity_response,
    entity_client,
    entity_path,
    entity_revision,
)

pytestmark = pytest.mark.django_db


def test_collection_selection_is_ordered_labeled_and_atomic():
    _, client = entity_client()
    books = [Book.objects.create(title=f"বই {number}") for number in range(3)]
    identifiers = [str(book.pk) for book in books[::-1]]
    response = create_entity_response(client, "collections", book_ids=identifiers)
    assert response.status_code == 201
    data = response.json()
    assert data["book_ids"] == identifiers
    assert data["selected_books"] == [
        {"id": str(book.pk), "name": book.title} for book in books[::-1]
    ]
    path = entity_path("collections", data["id"])
    invalid = client.patch(
        path,
        entity_revision(data, name="অকার্যকর", book_ids=[str(uuid4())]),
        format="json",
    )
    assert invalid.status_code == 400
    assert client.get(path).json() == data
    updated = client.patch(
        path, entity_revision(data, book_ids=identifiers[1:]), format="json"
    )
    assert updated.status_code == 200 and updated.json()["book_ids"] == identifiers[1:]
    emptied = client.patch(
        path, entity_revision(updated.json(), book_ids=[]), format="json"
    )
    assert emptied.status_code == 200 and emptied.json()["book_ids"] == []


def test_collection_details_batch_selected_book_labels(django_assert_num_queries):
    _, client = entity_client()
    books = [
        Book.objects.create(
            title=f"নির্বাচিত বই {index}", main_content_html="private-body"
        )
        for index in range(12)
    ]
    data = create_entity_response(
        client, "collections", book_ids=[str(book.pk) for book in books]
    ).json()
    with django_assert_num_queries(2):
        response = client.get(entity_path("collections", data["id"]))
    assert len(response.json()["selected_books"]) == 12
    assert "private-body" not in response.content.decode()


@pytest.mark.parametrize("selection", ["missing", "duplicate", "deleted", "over_limit"])
def test_invalid_book_selection_cannot_leave_a_collection_or_audit(selection):
    _, client = entity_client()
    book = Book.objects.create(title="সংকলনের বই")
    identifiers = [str(book.pk)]
    if selection == "missing":
        identifiers = [str(uuid4())]
    elif selection == "duplicate":
        identifiers *= 2
    elif selection == "deleted":
        from django.utils import timezone

        book.deleted_at = timezone.now()
        book.save()
    else:
        identifiers = [str(uuid4()) for _ in range(101)]
    response = create_entity_response(client, "collections", book_ids=identifiers)
    assert response.status_code == 400
    assert not CuratedCollection.objects.exists() and not AuditLog.objects.exists()


def test_collection_publication_review_withdrawal_and_redirects():
    _, client = entity_client()
    book = Book.objects.create(title="প্রকাশিত বই", state="published")
    data = create_entity_response(client, "collections", book_ids=[str(book.pk)]).json()
    path = entity_path("collections", data["id"])
    assert (
        client.post(
            path, entity_revision(data, action="publish"), format="json"
        ).status_code
        == 409
    )
    assert (
        client.post(
            path, entity_revision(data, action="review"), format="json"
        ).status_code
        == 400
    )
    reviewed = data
    assert (
        client.post(
            path, entity_revision(reviewed, action="publish"), format="json"
        ).status_code
        == 409
    )
    updated = client.patch(
        path,
        entity_revision(
            reviewed,
            editorial_description="নির্বাচিত বইয়ের সম্পাদকীয় পরিচিতি",
            indexing_eligible=True,
        ),
        format="json",
    ).json()
    reviewed = updated
    published = client.post(
        path, entity_revision(reviewed, action="publish"), format="json"
    )
    assert published.status_code == 200 and published.json()["state"] == "published"
    public = f"/api/v1/catalog/entities/collections/{data['slug']}/"
    assert client.get(public).status_code == 200
    renamed = client.patch(
        path, entity_revision(published.json(), name="নতুন নির্বাচিত সংগ্রহ"), format="json"
    ).json()
    assert client.get(public).status_code == 200
    reviewed = renamed
    redirect = client.get(public)
    assert redirect.status_code == 200 and redirect.json()["slug"] == reviewed["slug"]
    withdrawn = client.post(
        path, entity_revision(reviewed, action="withdraw"), format="json"
    )
    assert withdrawn.status_code == 200 and withdrawn.json()["state"] == "archived"
    assert client.get(public).status_code == 404
