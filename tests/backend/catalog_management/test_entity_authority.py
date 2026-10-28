from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.editorial.entity_service import entity_command, update_entity
from apps.catalog.models import Book, Category, Contributor
from apps.common.models import AuditLog
from django.http import Http404
from django.utils import timezone
from rest_framework.test import APIClient

from .entity_fixtures import (
    create_entity_response,
    entity_client,
    entity_path,
    entity_revision,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "kind,model,field",
    [
        ("contributors", Contributor, "contributor"),
        ("categories", Category, "category"),
    ],
)
def test_scoped_editors_manage_only_the_exact_granted_entity(kind, model, field):
    actor = User.objects.create_user(email="scoped-entity@library.test")
    selected = model.objects.create(name="অনুমোদিত পরিচিতি")
    other = model.objects.create(name="অন্য পরিচিতি")
    grant = PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.METADATA_EDIT, **{field: selected}
    )
    client = APIClient()
    client.force_authenticate(actor)
    assert [
        entry["id"] for entry in client.get(entity_path(kind)).json()["entries"]
    ] == [str(selected.pk)]
    assert client.get(entity_path(kind, other.pk)).status_code == 404
    data = client.get(entity_path(kind, selected.pk)).json()
    updated = client.patch(
        entity_path(kind, selected.pk),
        entity_revision(data, editorial_description="সীমিত সম্পাদনা"),
        format="json",
    )
    assert updated.status_code == 200
    assert create_entity_response(client, kind).status_code == 403
    assert not client.get(entity_path("series")).json()["entries"]
    grant.expires_at = timezone.now() - timedelta(seconds=1)
    grant.save()
    assert client.get(entity_path(kind, selected.pk)).status_code == 404


def test_book_scoped_permission_does_not_grant_entity_editing():
    actor = User.objects.create_user(email="book-scoped@library.test")
    book = Book.objects.create(title="অনুমোদিত বই")
    PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.METADATA_EDIT, book=book
    )
    contributor = Contributor.objects.create(name="অননুমোদিত লেখক")
    client = APIClient()
    client.force_authenticate(actor)
    assert client.get(entity_path("contributors")).json()["entries"] == []
    assert client.get(entity_path("contributors", contributor.pk)).status_code == 404


@pytest.mark.parametrize("field", ["is_active", "is_staff"])
@pytest.mark.parametrize("action", ["update", "review", "publish", "withdraw"])
def test_entity_mutations_reload_revoked_actor_authority(field, action):
    actor, client = entity_client()
    data = create_entity_response(client, "collections").json()
    from apps.catalog.models import CuratedCollection

    entity = CuratedCollection.objects.get(pk=data["id"])
    stale = User.objects.get(pk=actor.pk)
    User.objects.filter(pk=actor.pk).update(**{field: False})
    attributes = {"expected_updated_at": entity.updated_at}
    with pytest.raises(Http404):
        if action == "update":
            update_entity(
                stale, ("collections", entity.pk), {**attributes, "name": "নিষিদ্ধ"}
            )
        else:
            entity_command(
                stale, ("collections", entity.pk), {**attributes, "action": action}
            )
    entity.refresh_from_db()
    assert entity.name == data["name"] and AuditLog.objects.count() == 1


def test_readers_cannot_list_or_search_private_catalog_references():
    actor = User.objects.create_user(email="entity-reader@library.test")
    client = APIClient()
    client.force_authenticate(actor)
    assert client.get(entity_path("contributors")).status_code == 403
    assert (
        client.get("/api/v1/manage/catalog-references/?kind=books").status_code == 403
    )


def test_entity_lists_and_reference_searches_have_bounded_queries(
    django_assert_num_queries,
):
    actor, client = entity_client()
    for index in range(12):
        Contributor.objects.create(
            name=f"লেখক {index}",
            alternative_names=[f"বিকল্প {index}"],
            editorial_description="private-long-text" * 100,
        )
        Book.objects.create(title=f"বই {index}", summary="private-long-text" * 100)
    with django_assert_num_queries(2):
        listing = client.get(entity_path("contributors") + "?limit=5&q=বিকল্প")
    assert len(listing.json()["entries"]) == 5
    assert "private-long-text" not in listing.content.decode()
    with django_assert_num_queries(1):
        references = client.get(
            "/api/v1/manage/catalog-references/?kind=books&limit=5&q=বই"
        )
    assert len(references.json()["entries"]) == 5 and references.json()["has_more"]
    assert "private-long-text" not in references.content.decode()
    assert (
        client.get(
            "/api/v1/manage/catalog-references/?kind=books&limit=101"
        ).status_code
        == 400
    )
    actor.is_staff = False
    actor.save()
    permitted = Book.objects.first()
    PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.METADATA_EDIT, book=permitted
    )
    assert (
        client.get("/api/v1/manage/catalog-references/?kind=books").json()["entries"]
        == []
    )
