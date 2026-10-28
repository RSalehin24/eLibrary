from types import SimpleNamespace

import pytest
from apps.access.models import PermissionGrant, PermissionScope
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
    Series,
)
from apps.common.models import AuditLog
from rest_framework.test import APIClient

from .entity_fixtures import entity_client, entity_path

pytestmark = pytest.mark.django_db


@pytest.fixture(
    params=[
        ("contributors", Contributor, BookContributor, "contributor", "contributors"),
        ("categories", Category, BookCategory, "category", "category_ids"),
        ("series", Series, BookSeries, "series", "series_ids"),
    ]
)
def linked_entry(request):
    kind, model, relation, field, override = request.param
    entity = model.objects.create(name="বইয়ের সঙ্গে যুক্ত পরিচিতি")
    book = Book.objects.create(
        title="প্রকাশিত বই", state="published", metadata_overrides={"summary": "সারাংশ"}
    )
    relation.objects.create(book=book, **{field: entity})
    return SimpleNamespace(kind=kind, entity=entity, book=book, override=override)


def test_linked_entities_report_readonly_and_reject_nonadministrator_writes(
    linked_entry,
):
    item = linked_entry
    actor = User.objects.create_user(email="metadata-editor@library.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.METADATA_EDIT)
    client = APIClient()
    client.force_authenticate(actor)
    path = entity_path(item.kind, item.entity.pk)
    data = client.get(path).json()
    assert data["can_edit"] is False
    revision = item.book.updated_at
    response = client.patch(
        path,
        {"expected_updated_at": data["updated_at"], "name": "নিষিদ্ধ"},
        format="json",
    )
    assert response.status_code == 403
    item.entity.refresh_from_db()
    item.book.refresh_from_db()
    assert item.entity.name == data["name"] and item.book.updated_at == revision
    assert item.book.metadata_overrides == {"summary": "সারাংশ"}
    assert not AuditLog.objects.exists()


def test_administrator_entity_edit_preserves_publication_and_invalidates_book_drafts(
    linked_entry,
):
    item = linked_entry
    _, client = entity_client()
    path = entity_path(item.kind, item.entity.pk)
    data = client.get(path).json()
    assert data["can_edit"] is True
    revision = item.book.updated_at.isoformat()
    response = client.patch(
        path,
        {"expected_updated_at": data["updated_at"], "name": "সংশোধিত পরিচিতি"},
        format="json",
    )
    assert response.status_code == 200 and response.json()["can_edit"] is True
    item.book.refresh_from_db()
    assert (
        item.book.updated_at.isoformat() != revision and item.book.state == "published"
    )
    values = item.book.metadata_overrides[item.override]
    identifiers = (
        [entry["id"] for entry in values] if item.kind == "contributors" else values
    )
    assert identifiers == [str(item.entity.pk)]
    assert item.book.metadata_overrides["summary"] == "সারাংশ"
    stale = client.patch(
        f"/api/v1/manage/books/{item.book.slug}/",
        {"expected_updated_at": revision, "summary": "পুরনো খসড়া"},
        format="json",
    )
    assert stale.status_code == 409


def test_reading_list_curation_does_not_require_book_administration():
    actor = User.objects.create_user(email="list-curator@library.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.METADATA_EDIT)
    book = Book.objects.create(title="তালিকার বই", state="published")
    collection = CuratedCollection.objects.create(name="পাঠতালিকা")
    CollectionBook.objects.create(collection=collection, book=book)
    client = APIClient()
    client.force_authenticate(actor)
    path = entity_path("collections", collection.pk)
    data = client.get(path).json()
    assert data["can_edit"] is True
    revision = book.updated_at
    assert (
        client.patch(
            path,
            {"expected_updated_at": data["updated_at"], "book_ids": []},
            format="json",
        ).status_code
        == 200
    )
    book.refresh_from_db()
    assert book.updated_at == revision and not book.metadata_overrides
