from concurrent.futures import ThreadPoolExecutor
from threading import Event, get_ident
from time import monotonic, sleep
from unittest.mock import patch

import pytest
from apps.catalog.models import Book, Category, Contributor, Series
from apps.catalog.models import books as book_models
from apps.catalog.models import entities as entity_models
from django.db import close_old_connections, connection, connections

pytestmark = pytest.mark.django_db(transaction=True)


def wait_until_competing_allocation_is_observed(state):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        if state["second_allocated"].is_set():
            return
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s",
                [state["second_pid"]],
            )
            if cursor.fetchone() == ("Lock",):
                return
        sleep(0.01)
    raise AssertionError("The competing catalog allocation did not become observable.")


@pytest.mark.parametrize(
    "allocation_case",
    [
        (Contributor, entity_models, "next_entity_sequence", "name"),
        (Category, entity_models, "next_entity_sequence", "name"),
        (Series, entity_models, "next_entity_sequence", "name"),
        (Book, book_models, "build_book_catalog_code", "title"),
    ],
)
def test_model_creation_serializes_catalog_code_allocation(allocation_case):
    model, module, method, display_field = allocation_case
    original = getattr(module, method)
    state = {
        name: Event()
        for name in [
            "first_allocated",
            "release_first",
            "second_started",
            "second_allocated",
        ]
    }

    def controlled_allocation(*args, **kwargs):
        code = original(*args, **kwargs)
        if get_ident() == state["first_thread"]:
            state["first_allocated"].set()
            assert state["release_first"].wait(timeout=10)
        else:
            state["second_allocated"].set()
        return code

    def create_record(name):
        close_old_connections()
        try:
            if name == "first":
                state["first_thread"] = get_ident()
            else:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    state["second_pid"] = cursor.fetchone()[0]
                state["second_started"].set()
            return model.objects.create(**{display_field: name}).catalog_code
        finally:
            connections.close_all()

    with (
        patch.object(module, method, side_effect=controlled_allocation),
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        first = pool.submit(create_record, "first")
        try:
            assert state["first_allocated"].wait(timeout=10)
            second = pool.submit(create_record, "second")
            assert state["second_started"].wait(timeout=10)
            wait_until_competing_allocation_is_observed(state)
        finally:
            state["release_first"].set()
        assert first.result(timeout=10) != second.result(timeout=10)
    assert model.objects.count() == 2
