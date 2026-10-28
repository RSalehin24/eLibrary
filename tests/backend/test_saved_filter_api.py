from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.common.models import SavedFilter
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PATH = "/api/v1/me/saved-filters/"


def account_client(name):
    actor = User.objects.create_user(email=f"{name}@example.test")
    client = APIClient()
    client.force_authenticate(actor)
    return actor, client


def definition(**changes):
    return {
        "operation_id": str(uuid4()),
        "target": "catalog",
        "name": "Saved catalog",
        "params": {"q": "বাংলা", "sort": "title"},
        **changes,
    }


def test_saved_filters_are_private_owner_scoped_idempotent_and_deletable():
    actor, client = account_client("saved-owner")
    values = definition()
    created = client.post(PATH, values, format="json")
    assert (
        created.status_code == 201 and created["Cache-Control"] == "private, no-store"
    )
    assert (
        created.json()["params"] == values["params"] and "owner" not in created.json()
    )
    assert client.post(PATH, values, format="json").json()["id"] == created.json()["id"]
    assert SavedFilter.objects.filter(owner=actor).count() == 1
    assert client.get(PATH).json()["entries"] == [created.json()]
    _, other = account_client("saved-stranger")
    assert other.get(PATH).json()["entries"] == []
    assert other.delete(PATH + created.json()["id"] + "/").status_code == 404
    assert other.post(PATH, values, format="json").status_code == 409
    assert client.delete(PATH + created.json()["id"] + "/").status_code == 204
    assert not SavedFilter.objects.exists()
    assert APIClient().get(PATH).status_code == 403


@pytest.mark.parametrize(
    "changes",
    [
        {"params": {"raw_scrape_payload": "private"}},
        {"owner": 999},
        {"name": ""},
        {"params": {"sort": "raw_scrape_payload"}},
        {"params": {"q": "x" * 121}},
        {"params": {"q": ["invalid"]}},
        {"params": {"page": "2"}},
        {"target": "private-users"},
        {"target": "queue", "params": {"kind": "unknown"}},
    ],
)
def test_invalid_saved_filter_inputs_do_not_create_rows(changes):
    _, client = account_client("saved-invalid")
    assert client.post(PATH, definition(**changes), format="json").status_code == 400
    assert not SavedFilter.objects.exists()


def test_saved_filter_name_and_operation_conflicts_preserve_existing_conditions():
    _, client = account_client("saved-conflict")
    values = definition()
    created = client.post(PATH, values, format="json").json()
    assert (
        client.post(PATH, definition(name=values["name"]), format="json").status_code
        == 409
    )
    assert (
        client.post(
            PATH, {**values, "params": {"q": "different"}}, format="json"
        ).status_code
        == 409
    )
    assert client.get(PATH).json()["entries"] == [created]


def test_saved_queue_conditions_are_validated_without_granting_queue_access():
    _, client = account_client("saved-queue")
    created = client.post(
        PATH,
        definition(
            target="queue", params={"state": "retry_wait", "kind": "process_source"}
        ),
        format="json",
    )
    assert created.status_code == 201
    assert (
        client.get(PATH, {"target": "queue"}).json()["entries"][0]["id"]
        == created.json()["id"]
    )
    assert not client.get(PATH, {"target": "catalog"}).json()["entries"]
    assert client.get("/api/v1/manage/jobs/").status_code == 403


def test_saved_queue_search_and_diagnostic_conditions_remain_owner_scoped():
    _, client = account_client("saved-queue-diagnostics")
    conditions = {
        "view": "recovery",
        "q": "বাংলা",
        "coverage": "incomplete",
        "error_code": "source_content_incomplete",
    }
    created = client.post(
        PATH, definition(target="queue", params=conditions), format="json"
    )
    assert created.status_code == 201 and created.json()["params"] == conditions
    _, stranger = account_client("saved-queue-diagnostics-stranger")
    assert not stranger.get(PATH, {"target": "queue"}).json()["entries"]
    assert stranger.delete(PATH + created.json()["id"] + "/").status_code == 404


def test_saved_filter_limit_preserves_existing_filters_and_pagination():
    actor, client = account_client("saved-limit")
    SavedFilter.objects.bulk_create(
        [
            SavedFilter(owner=actor, target="catalog", name=f"Filter {index:03d}")
            for index in range(100)
        ]
    )
    assert client.post(PATH, definition(), format="json").status_code == 400
    first = client.get(PATH, {"limit": 50}).json()
    second = client.get(PATH, {"limit": 50, "page": 2}).json()
    assert first["pagination"]["total_count"] == 100
    assert len(first["entries"]) == len(second["entries"]) == 50
    assert {entry["id"] for entry in first["entries"]}.isdisjoint(
        entry["id"] for entry in second["entries"]
    )
