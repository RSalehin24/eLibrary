from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, get_ident
from unittest.mock import patch
from uuid import uuid4

import pytest
from apps.catalog.editorial.entity_service import create_entity
from apps.catalog.editorial.service import EditorialConflict
from apps.catalog.locking import lock_title
from apps.catalog.models import (
    Book,
    BookGroup,
    Contributor,
    CuratedCollection,
    MetadataVersion,
)
from apps.common.models import AuditLog
from django.db import close_old_connections, connections, transaction
from rest_framework.test import APIClient

from .entity_fixtures import entity_client, entity_path, entity_revision

pytestmark = pytest.mark.django_db(transaction=True)


def request_at_barrier(actor, request, barrier):
    close_old_connections()
    try:
        client = APIClient()
        client.force_authenticate(actor)
        method, path, values = request
        barrier.wait(timeout=10)
        response = getattr(client, method)(path, values, format="json")
        return response.status_code, response.json()
    finally:
        connections.close_all()


def concurrent_requests(actors, requests):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(request_at_barrier, actor, request, barrier)
            for actor, request in zip(actors, requests)
        ]
        return [future.result(timeout=15) for future in futures]


def creation(kind, values):
    return "post", entity_path(kind), values


def test_same_actor_repeated_creation_makes_one_entity_and_audit():
    actor, _ = entity_client()
    values = {"operation_id": str(uuid4()), "name": "সমান্তরাল লেখক"}
    request = creation("contributors", values)
    results = concurrent_requests([actor, actor], [request, request])
    assert [status for status, _ in results] == [201, 201]
    assert results[0][1] == results[1][1]
    assert Contributor.objects.count() == AuditLog.objects.count() == 1


@pytest.mark.parametrize(
    "kind,model", [("contributors", Contributor), ("collections", CuratedCollection)]
)
def test_concurrent_creators_cannot_duplicate_a_name(kind, model):
    actors = [entity_client()[0] for _ in range(2)]
    requests = [
        creation(kind, {"operation_id": str(uuid4()), "name": "একই পরিচিতি"})
        for _ in actors
    ]
    results = concurrent_requests(actors, requests)
    assert sorted(status for status, _ in results) == [201, 400]
    assert model.objects.count() == AuditLog.objects.count() == 1


def test_cross_kind_uuid_collision_rolls_back_the_losing_entity():
    actors = [entity_client()[0] for _ in range(2)]
    identifier = str(uuid4())
    requests = [
        creation(kind, {"operation_id": identifier, "name": "নতুন পরিচিতি"})
        for kind in ["contributors", "collections"]
    ]
    results = concurrent_requests(actors, requests)
    assert sorted(status for status, _ in results) == [201, 409]
    assert Contributor.objects.count() + CuratedCollection.objects.count() == 1
    assert AuditLog.objects.count() == 1


def test_parallel_updates_accept_only_one_expected_revision():
    actors = [entity_client()[0] for _ in range(2)]
    entity = Contributor.objects.create(name="এক লেখকের দুই সম্পাদক")
    requests = [
        (
            "patch",
            entity_path("contributors", entity.pk),
            {
                "expected_updated_at": entity.updated_at.isoformat(),
                "name": f"সম্পাদনা {index}",
            },
        )
        for index in range(2)
    ]
    results = concurrent_requests(actors, requests)
    assert sorted(status for status, _ in results) == [200, 409]
    assert AuditLog.objects.count() == 1


def test_concurrent_collection_renames_cannot_duplicate_names():
    actors = [entity_client()[0] for _ in range(2)]
    entities = [
        CuratedCollection.objects.create(name=f"সংগ্রহ {index}") for index in range(2)
    ]
    requests = [
        (
            "patch",
            entity_path("collections", entity.pk),
            entity_revision(
                {"updated_at": entity.updated_at.isoformat()}, name="একই সংগ্রহ"
            ),
        )
        for entity in entities
    ]
    results = concurrent_requests(actors, requests)
    assert sorted(status for status, _ in results) == [200, 400]
    assert CuratedCollection.objects.filter(name="একই সংগ্রহ").count() == 1


def edition_request(book, sibling):
    return (
        "patch",
        f"/api/v1/manage/books/{book.slug}/relationships/",
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "edition_of": str(sibling.pk),
        },
    )


def test_parallel_relationship_edits_accept_one_revision():
    actors = [entity_client()[0] for _ in range(2)]
    book = Book.objects.create(title="একই সম্পর্কের সম্পাদনা")
    request = (
        "patch",
        f"/api/v1/manage/books/{book.slug}/relationships/",
        {"expected_updated_at": book.updated_at.isoformat(), "category_ids": []},
    )
    results = concurrent_requests(actors, [request, request])
    assert sorted(status for status, _ in results) == [200, 409]
    assert MetadataVersion.objects.count() == 1


def test_parallel_editions_join_one_new_group():
    actors = [entity_client()[0] for _ in range(2)]
    books = [Book.objects.create(title=f"নতুন সংস্করণ {index}") for index in range(2)]
    sibling = Book.objects.create(title="মূল সংস্করণ")
    results = concurrent_requests(
        actors, [edition_request(book, sibling) for book in books]
    )
    assert [status for status, _ in results] == [200, 200]
    assert BookGroup.objects.count() == 1 and MetadataVersion.objects.count() == 3
    assert len({entry["group_id"] for _, entry in results}) == 1


def test_reciprocal_edition_commands_do_not_deadlock_or_use_a_stale_revision():
    actors = [entity_client()[0] for _ in range(2)]
    books = [Book.objects.create(title=f"পারস্পরিক সংস্করণ {index}") for index in range(2)]
    requests = [
        edition_request(books[0], books[1]),
        edition_request(books[1], books[0]),
    ]
    results = concurrent_requests(actors, requests)
    assert sorted(status for status, _ in results) == [200, 409]
    assert BookGroup.objects.count() == 1 and MetadataVersion.objects.count() == 2


def assert_creation_collision(actor, identifier):
    with pytest.raises(EditorialConflict):
        create_entity(
            actor, "contributors", {"operation_id": identifier, "name": "আরেক পরিচিতি"}
        )


def test_existing_uuid_collision_and_edit_take_kind_lock_before_entity_lock():
    editor, _ = entity_client()
    creator, _ = entity_client()
    entity = Contributor.objects.create(name="আগের লেখকের নথি")
    attempt = Event()
    creating_thread = get_ident()

    def notify_lock(title):
        if get_ident() != creating_thread:
            attempt.set()
        lock_title(title)

    request = (
        "patch",
        entity_path("contributors", entity.pk),
        {"expected_updated_at": entity.updated_at.isoformat(), "name": "সম্পাদিত নথি"},
    )
    with (
        patch(
            "apps.catalog.editorial.entity_service.lock_title", side_effect=notify_lock
        ),
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        with transaction.atomic():
            lock_title("catalog-entity:contributors")
            edit = executor.submit(request_at_barrier, editor, request, Barrier(1))
            assert attempt.wait(timeout=10)
            assert_creation_collision(creator, entity.pk)
        status, data = edit.result(timeout=15)
    assert status == 200 and data["name"] == "সম্পাদিত নথি"
    assert Contributor.objects.count() == AuditLog.objects.count() == 1
