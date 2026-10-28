from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from apps.common.models import AuditLog
from django.db import close_old_connections, connections
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(transaction=True)


def create_at_barrier(actor, values, barrier):
    close_old_connections()
    try:
        client = APIClient()
        client.force_authenticate(actor)
        barrier.wait(timeout=10)
        response = client.post("/api/v1/manage/books/", values, format="json")
        return response.status_code, response.json()
    finally:
        connections.close_all()


def concurrent_creations(actors, commands):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(create_at_barrier, actor, values, barrier)
            for actor, values in zip(actors, commands)
        ]
        return [future.result(timeout=15) for future in futures]


def creator(email):
    return User.objects.create_user(email=email, is_staff=True)


def test_parallel_repeated_creation_produces_one_book_and_audit():
    actor = creator("parallel-creator@library.test")
    values = {"operation_id": str(uuid4()), "title": "এক অনুরোধের বই"}
    results = concurrent_creations([actor, actor], [values, values])
    assert all(status == 201 for status, _ in results)
    assert results[0][1]["id"] == results[1][1]["id"]
    assert Book.objects.count() == AuditLog.objects.count() == 1
    assert not UserBook.objects.exists()


def test_different_creators_can_enter_editions_with_the_same_title():
    actors = [creator(f"edition-{index}@library.test") for index in range(2)]
    commands = [
        {
            "operation_id": str(uuid4()),
            "title": "একই নামের পৃথক সংস্করণ",
            "edition": str(index),
        }
        for index in range(2)
    ]
    results = concurrent_creations(actors, commands)
    assert all(status == 201 for status, _ in results)
    assert Book.objects.count() == AuditLog.objects.count() == 2
    assert results[0][1]["slug"] != results[1][1]["slug"]


def test_cross_account_identifier_collision_cannot_return_another_creation():
    actors = [creator(f"collision-{index}@library.test") for index in range(2)]
    identifier = str(uuid4())
    commands = [
        {"operation_id": identifier, "title": f"পৃথক বই {index}"} for index in range(2)
    ]
    results = concurrent_creations(actors, commands)
    assert sorted(status for status, _ in results) == [201, 409]
    assert Book.objects.count() == AuditLog.objects.count() == 1
