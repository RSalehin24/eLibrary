from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.editorial.relationships import update_relationships
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookGroup,
    BookSeries,
    Category,
    Contributor,
    MetadataVersion,
    Series,
)
from django.http import Http404
from django.utils import timezone
from rest_framework.test import APIClient

from .entity_fixtures import entity_client, entity_revision

pytestmark = pytest.mark.django_db


def relationship_fixture():
    _, client = entity_client()
    book = Book.objects.create(title="সম্পর্কের বই", state="published")
    path = f"/api/v1/manage/books/{book.slug}/relationships/"
    contributor = Contributor.objects.create(name="দুই ভূমিকার সহযোগী")
    category = Category.objects.create(name="নির্বাচিত বিভাগ")
    series = Series.objects.create(name="নির্বাচিত সিরিজ")
    return (
        client,
        book,
        path,
        {
            "contributors": [
                {"id": str(contributor.pk), "role": role}
                for role in ["author", "translator"]
            ],
            "category_ids": [str(category.pk)],
            "series_ids": [str(series.pk)],
        },
    )


def test_relationship_edits_preserve_roles_snapshot_and_require_new_review():
    client, book, path, values = relationship_fixture()
    data = client.get(path).json()
    response = client.patch(path, entity_revision(data, **values), format="json")
    assert response.status_code == 200
    assert [entry["role"] for entry in response.json()["contributors"]] == [
        "author",
        "translator",
    ]
    assert response.json()["categories"][0]["id"] == values["category_ids"][0]
    assert response.json()["series"][0]["id"] == values["series_ids"][0]
    snapshot = MetadataVersion.objects.get().snapshot
    assert snapshot == {
        "contributors": [],
        "category_ids": [],
        "series_ids": [],
        "group_id": None,
    }
    book.refresh_from_db()
    assert not hasattr(book, "editorial_reviewed_at") and (
        not hasattr(book, "review_state")
    )
    assert (
        client.patch(path, entity_revision(data, **values), format="json").status_code
        == 409
    )
    assert MetadataVersion.objects.count() == 1
    removed = client.patch(
        path,
        entity_revision(
            response.json(), contributors=[], category_ids=[], series_ids=[]
        ),
        format="json",
    )
    assert removed.status_code == 200
    assert (
        not BookContributor.objects.exists()
        and not BookCategory.objects.exists()
        and not BookSeries.objects.exists()
    )


@pytest.mark.parametrize(
    "invalid",
    [
        "missing",
        "duplicate",
        "unknown_role",
        "over_limit",
        "over_limit_contributors",
        "unknown_field",
    ],
)
def test_invalid_relationships_roll_back_every_change(invalid):
    client, book, path, values = relationship_fixture()
    data = client.get(path).json()
    if invalid == "missing":
        values["series_ids"] = [str(uuid4())]
    elif invalid == "duplicate":
        values["contributors"] *= 2
    elif invalid == "unknown_role":
        values["contributors"][0]["role"] = "made-up"
    elif invalid == "over_limit":
        values["category_ids"] = [str(uuid4()) for _ in range(101)]
    elif invalid == "over_limit_contributors":
        values["contributors"] = [
            {"id": str(uuid4()), "role": "author"} for _ in range(101)
        ]
    else:
        values["contributors"][0]["extra"] = True
    response = client.patch(path, entity_revision(data, **values), format="json")
    assert response.status_code == 400
    assert client.get(path).json() == data
    assert not MetadataVersion.objects.exists() and not BookContributor.objects.exists()
    book.refresh_from_db()
    assert not hasattr(book, "review_state")


def test_explicit_edition_selection_joins_moves_and_detaches_one_book():
    client, _, path, _ = relationship_fixture()
    sibling = Book.objects.create(title="আগের সংস্করণ")
    initial = client.get(path).json()
    joined = client.patch(
        path, entity_revision(initial, edition_of=str(sibling.pk)), format="json"
    )
    assert joined.status_code == 200
    sibling.refresh_from_db()
    assert joined.json()["group_id"] == str(sibling.group_id)
    assert joined.json()["related_editions"] == [
        {
            "id": str(sibling.pk),
            "name": sibling.title,
            "catalog_code": sibling.catalog_code,
        }
    ]
    assert not hasattr(sibling, "review_state") and (
        not hasattr(sibling, "editorial_reviewed_at")
    )
    assert MetadataVersion.objects.count() == 2
    different = Book.objects.create(title="অন্য কাজের সংস্করণ")
    moved = client.patch(
        path,
        entity_revision(joined.json(), edition_of=str(different.pk)),
        format="json",
    ).json()
    assert (
        moved["group_id"] != joined.json()["group_id"]
        and BookGroup.objects.count() == 2
    )
    sibling.refresh_from_db()
    assert str(sibling.group_id) == joined.json()["group_id"]
    detached = client.patch(
        path, entity_revision(moved, edition_of=None), format="json"
    )
    assert detached.status_code == 200 and detached.json()["group_id"] is None
    assert detached.json()["related_editions"] == []


@pytest.mark.parametrize("selection", ["self", "missing", "deleted"])
def test_invalid_edition_selection_is_atomic(selection):
    client, book, path, values = relationship_fixture()
    identifier = book.pk if selection == "self" else uuid4()
    if selection == "deleted":
        sibling = Book.objects.create(title="অপসারিত সংস্করণ", deleted_at=timezone.now())
        identifier = sibling.pk
    data = client.get(path).json()
    response = client.patch(
        path, entity_revision(data, **values, edition_of=str(identifier)), format="json"
    )
    assert response.status_code == (400 if selection == "self" else 404)
    assert client.get(path).json() == data
    assert not MetadataVersion.objects.exists() and not BookGroup.objects.exists()


def test_scoped_editors_cannot_change_relationships_that_determine_permissions():
    _, book, path, values = relationship_fixture()
    actor = User.objects.create_user(email="relationship-scoped@library.test")
    PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.METADATA_EDIT, book=book
    )
    client = APIClient()
    client.force_authenticate(actor)
    assert client.get(path).status_code == 403
    response = client.patch(
        path,
        {"expected_updated_at": book.updated_at.isoformat(), **values},
        format="json",
    )
    assert response.status_code == 403 and not MetadataVersion.objects.exists()


def test_relationship_mutations_reload_actor_authority_and_enforce_csrf():
    actor, client = entity_client()
    book = Book.objects.create(title="বর্তমান সম্পর্কের অনুমতি")
    path = f"/api/v1/manage/books/{book.slug}/relationships/"
    data = client.get(path).json()
    csrf_client = APIClient(enforce_csrf_checks=True)
    csrf_client.force_login(actor)
    assert (
        csrf_client.patch(
            path, entity_revision(data, category_ids=[]), format="json"
        ).status_code
        == 403
    )
    stale = User.objects.get(pk=actor.pk)
    User.objects.filter(pk=actor.pk).update(is_staff=False)
    with pytest.raises(Http404):
        update_relationships(
            stale, book.pk, {"expected_updated_at": book.updated_at, "category_ids": []}
        )
    assert not MetadataVersion.objects.exists()


def test_relationship_order_and_history_keep_the_previous_selection():
    client, _, path, values = relationship_fixture()
    second = Series.objects.create(name="অন্য সিরিজ")
    values["series_ids"].append(str(second.pk))
    data = client.get(path).json()
    first = client.patch(path, entity_revision(data, **values), format="json").json()
    reversed_values = {
        "contributors": values["contributors"][::-1],
        "series_ids": values["series_ids"][::-1],
    }
    reversed_data = client.patch(
        path, entity_revision(first, **reversed_values), format="json"
    )
    assert reversed_data.status_code == 200
    assert [entry["role"] for entry in reversed_data.json()["contributors"]] == [
        "translator",
        "author",
    ]
    assert [entry["id"] for entry in reversed_data.json()["series"]] == reversed_values[
        "series_ids"
    ]
    assert (
        MetadataVersion.objects.first().snapshot["contributors"]
        == values["contributors"]
    )
    assert (
        MetadataVersion.objects.first().snapshot["series_ids"] == values["series_ids"]
    )
