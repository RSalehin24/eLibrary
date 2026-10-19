import pytest
from apps.catalog.models import Book, BookContributor, Contributor
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def directory_records():
    first = Contributor.objects.create(name="Alpha")
    second = Contributor.objects.create(name="Beta")
    hidden = Contributor.objects.create(name="Private writer")
    digital = Book.objects.create(title="Digital", state="published")
    paper = Book.objects.create(title="Paper", state="published", record_type="manual")
    private = Book.objects.create(title="Private", state="draft")
    for writer, book, role in [
        (first, digital, "author"),
        (first, digital, "translator"),
        (first, paper, "author"),
        (second, digital, "translator"),
        (second, private, "author"),
        (hidden, private, "author"),
    ]:
        BookContributor.objects.create(contributor=writer, book=book, role=role)
    return first, second


def test_directory_counts_visible_books_once_and_combines_role_with_type():
    first, second = directory_records()
    client = APIClient()
    response = client.get("/api/v1/catalog/entities/contributors/", {"sort": "name"})
    assert response.status_code == 200
    assert [
        (entry["name"], entry["book_count"]) for entry in response.json()["entries"]
    ] == [(first.name, 2), (second.name, 1)]
    filtered = client.get(
        "/api/v1/catalog/entities/contributors/",
        {"sort": "-book_count", "role": "author", "record_type": "manual"},
    )
    assert [
        (entry["id"], entry["book_count"]) for entry in filtered.json()["entries"]
    ] == [(str(first.pk), 1)]
    assert not client.get(
        "/api/v1/catalog/entities/contributors/",
        {"role": "translator", "record_type": "manual"},
    ).json()["entries"]


@pytest.mark.parametrize(
    "ordering,reverse",
    [("name", False), ("-name", True), ("book_count", True), ("-book_count", False)],
)
def test_directory_sort_cursors_preserve_order_and_filter_context(ordering, reverse):
    records = directory_records()
    expected = list(reversed(records)) if reverse else list(records)
    client = APIClient()
    parameters = {"sort": ordering, "limit": 1}
    first = client.get("/api/v1/catalog/entities/contributors/", parameters)
    assert first.status_code == 200 and first.json()["has_more"]
    cursor = first.json()["next_cursor"]
    second = client.get(
        "/api/v1/catalog/entities/contributors/", {**parameters, "cursor": cursor}
    )
    assert second.status_code == 200 and not second.json()["has_more"]
    assert [page.json()["entries"][0]["id"] for page in [first, second]] == [
        str(writer.pk) for writer in expected
    ]
    assert (
        client.get(
            "/api/v1/catalog/entities/contributors/",
            {**parameters, "record_type": "manual", "cursor": cursor},
        ).status_code
        == 400
    )


def test_directory_rejects_unsupported_sort_type_and_role_scope():
    client = APIClient()
    for parameters in [{"sort": "raw_metadata"}, {"record_type": "private"}]:
        assert (
            client.get("/api/v1/catalog/entities/contributors/", parameters).status_code
            == 400
        )
    assert (
        client.get(
            "/api/v1/catalog/entities/categories/", {"role": "author"}
        ).status_code
        == 400
    )
