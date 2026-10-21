from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    CollectionBook,
    Contributor,
    CuratedCollection,
    Series,
)

pytestmark = pytest.mark.django_db
DIRECTORY = "/api/v1/catalog/entities/"
RELATIONS = [
    ("contributors", Contributor, BookContributor, "contributor"),
    ("categories", Category, BookCategory, "category"),
    ("series", Series, BookSeries, "series"),
]


def related_entities(relation):
    _kind, model, link, field = relation
    book = Book.objects.create(title="প্রকাশিত সম্পর্কের বই", state="published")
    entities = [model.objects.create(name=f"পরিচয় {number}") for number in range(3)]
    for entity in entities:
        link.objects.create(book=book, **{field: entity})
    return entities


@pytest.mark.parametrize("relation", RELATIONS)
@pytest.mark.parametrize(
    "ordering", ["catalog_code", "-catalog_code", "created_at", "-created_at"]
)
def test_entity_code_and_creation_sort_cursors_are_stable(client, relation, ordering):
    records = related_entities(relation)
    model = relation[1]
    timestamp = datetime(2026, 1, 2, 12, tzinfo=ZoneInfo("UTC"))
    model.objects.filter(pk__in=[record.pk for record in records]).update(
        created_at=timestamp
    )
    key = (
        (lambda record: (record.catalog_code or "", record.pk))
        if "catalog_code" in ordering
        else (lambda record: record.pk)
    )
    expected = sorted(records, key=key, reverse=ordering.startswith("-"))
    parameters = {"sort": ordering, "limit": 1}
    path = f"{DIRECTORY}{relation[0]}/"
    pages = []
    for _index in range(3):
        response = client.get(path, parameters)
        assert response.status_code == 200
        payload = response.json()
        pages.extend(payload["entries"])
        parameters["cursor"] = payload["next_cursor"]
    assert [entry["id"] for entry in pages] == [str(record.pk) for record in expected]
    assert all(entry["catalog_code"] for entry in pages)
    assert all(
        datetime.fromisoformat(entry["created_at"]) == timestamp for entry in pages
    )
    assert parameters["cursor"] is None


@pytest.mark.parametrize("relation", RELATIONS)
def test_entity_dates_include_the_whole_dhaka_day_and_bind_cursor(client, relation):
    entities = related_entities(relation)
    timestamps = [
        "2026-01-01T17:59:59+00:00",
        "2026-01-01T18:00:00+00:00",
        "2026-01-02T17:59:59+00:00",
    ]
    for entity, timestamp in zip(entities, timestamps):
        relation[1].objects.filter(pk=entity.pk).update(
            created_at=datetime.fromisoformat(timestamp)
        )
    path = f"{DIRECTORY}{relation[0]}/"
    parameters = {
        "created_after": "2026-01-02",
        "created_before": "2026-01-02",
        "sort": "created_at",
        "limit": 1,
    }
    first = client.get(path, parameters)
    assert first.status_code == 200
    assert first.json()["entries"][0]["id"] == str(entities[1].pk)
    cursor = first.json()["next_cursor"]
    next_page = client.get(path, {**parameters, "cursor": cursor})
    assert next_page.status_code == 200
    assert next_page.json()["entries"][0]["id"] == str(entities[2].pk)
    assert not next_page.json()["has_more"]
    assert (
        client.get(
            path, {**parameters, "created_before": "2026-01-03", "cursor": cursor}
        ).status_code
        == 400
    )
    assert client.get(path, {"sort": "created_at", "cursor": cursor}).status_code == 400


@pytest.mark.parametrize("relation", RELATIONS)
def test_directory_catalog_number_search_retains_exact_identity(client, relation):
    records = related_entities(relation)
    response = client.get(
        f"{DIRECTORY}{relation[0]}/", {"q": records[1].catalog_code.lower()}
    )
    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()["entries"]] == [str(records[1].pk)]


@pytest.mark.parametrize(
    "parameters",
    [
        {"created_after": "2026-02-30"},
        {"created_before": "not-a-date"},
        {"created_after": "2026-01-03", "created_before": "2026-01-02"},
    ],
)
def test_directory_rejects_invalid_and_reversed_dates(client, parameters):
    assert client.get(f"{DIRECTORY}contributors/", parameters).status_code == 400


def test_collections_have_creation_metadata_and_reject_catalog_code_sort(client):
    collection = CuratedCollection.objects.create(
        name="নির্বাচিত", state="published", editorial_description="প্রকাশিত পরিচয়"
    )
    book = Book.objects.create(title="নির্বাচিত বই", state="published")
    CollectionBook.objects.create(collection=collection, book=book)
    response = client.get(f"{DIRECTORY}collections/", {"sort": "created_at"})
    assert response.status_code == 200
    assert response.json()["entries"][0]["catalog_code"] is None
    assert response.json()["entries"][0]["created_at"]
    for ordering in ["catalog_code", "-catalog_code"]:
        assert (
            client.get(f"{DIRECTORY}collections/", {"sort": ordering}).status_code
            == 400
        )
