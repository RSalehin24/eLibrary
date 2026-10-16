from uuid import uuid4

import pytest
from apps.catalog.models import Contributor
from apps.common.models import AuditLog
from rest_framework.test import APIClient

from .entity_fixtures import (
    create_entity_response,
    entity_client,
    entity_path,
    entity_revision,
)

pytestmark = pytest.mark.django_db
KINDS = ["contributors", "categories", "series", "collections"]


@pytest.mark.parametrize("kind", KINDS)
def test_entity_creation_replay_revision_review_and_slug_history(kind):
    actor, client = entity_client()
    identifier = str(uuid4())
    values = {"operation_id": identifier, "editorial_description": "যাচাইকৃত পরিচিতি"}
    response = create_entity_response(client, kind, **values)
    assert response.status_code == 201
    original = response.json()
    path = entity_path(kind, identifier)
    assert original["id"] == identifier and original["editorial_reviewed_at"] is None
    assert response["Cache-Control"] == "private, no-store"
    assert create_entity_response(client, kind, **values).json() == original
    reviewed = client.post(
        path, entity_revision(original, action="review"), format="json"
    )
    assert reviewed.status_code == 200 and reviewed.json()["editorial_reviewed_at"]
    updated = client.patch(
        path, entity_revision(reviewed.json(), name="পরিবর্তিত পরিচিতি"), format="json"
    )
    assert (
        updated.status_code == 200 and updated.json()["editorial_reviewed_at"] is None
    )
    assert updated.json()["slug"] != original["slug"]
    assert create_entity_response(client, kind, **values).json() == updated.json()
    assert (
        client.patch(
            path, entity_revision(original, name="পুরনো"), format="json"
        ).status_code
        == 409
    )
    assert (
        client.post(
            path, entity_revision(original, action="review"), format="json"
        ).status_code
        == 409
    )
    audit = AuditLog.objects.get(pk=identifier)
    assert audit.actor == actor and audit.target_id == identifier


def test_creation_rejects_existing_identifier_without_overwriting_entity():
    _, client = entity_client()
    existing = Contributor.objects.create(name="আগের লেখক")
    response = create_entity_response(client, operation_id=str(existing.pk))
    assert response.status_code == 409
    existing.refresh_from_db()
    assert existing.name == "আগের লেখক" and not AuditLog.objects.exists()


def test_replay_verifies_audit_target_and_command_owner():
    _, client = entity_client()
    values = {"operation_id": str(uuid4())}
    original = create_entity_response(client, **values).json()
    assert create_entity_response(client, **values, name="অন্য নাম").status_code == 409
    _, other = entity_client()
    assert create_entity_response(other, **values).status_code == 409
    AuditLog.objects.filter(pk=original["id"]).update(target_id=str(uuid4()))
    assert create_entity_response(client, **values).status_code == 409
    assert Contributor.objects.get().name == original["name"]


@pytest.mark.parametrize("kind", KINDS)
def test_duplicate_normalized_names_are_rejected_on_creation_and_update(kind):
    _, client = entity_client()
    original = create_entity_response(client, kind, name="একই  নাম")
    assert original.status_code == 201
    assert create_entity_response(client, kind, name="একই নাম").status_code == 400
    second = create_entity_response(client, kind, name="আলাদা নাম").json()
    response = client.patch(
        entity_path(kind, second["id"]),
        entity_revision(second, name="একই নাম"),
        format="json",
    )
    assert response.status_code in {400, 409}
    assert client.get(entity_path(kind, second["id"])).json()["name"] == "আলাদা নাম"


@pytest.mark.parametrize(
    "values,field",
    [
        ({"name": "!!!"}, "name"),
        ({"state": "published"}, "state"),
        ({"alternative_names": ["!!!"]}, "alternative_names"),
        ({"social_image_url": "http://example.test/image.png"}, "social_image_url"),
        ({"book_ids": [str(uuid4())]}, "book_ids"),
    ],
)
def test_invalid_entity_creation_rolls_back(values, field):
    _, client = entity_client()
    response = create_entity_response(client, **values)
    assert response.status_code == 400 and field in response.json()["field_errors"]
    assert not Contributor.objects.exists() and not AuditLog.objects.exists()


def test_entity_session_writes_require_csrf():
    actor, _ = entity_client()
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(actor)
    assert create_entity_response(client).status_code == 403
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    response = client.post(
        entity_path("contributors"),
        {"operation_id": str(uuid4()), "name": "নতুন লেখক"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 201
    path, data = entity_path("contributors", response.json()["id"]), response.json()
    assert (
        client.patch(
            path, entity_revision(data, name="পরিবর্তন"), format="json"
        ).status_code
        == 403
    )
    assert (
        client.post(
            path, entity_revision(data, action="review"), format="json"
        ).status_code
        == 403
    )


def test_unknown_kinds_and_invalid_parameters_are_bounded():
    _, client = entity_client()
    assert client.get(entity_path("unknown")).status_code == 404
    assert create_entity_response(client, "unknown").status_code == 404
    assert client.get(entity_path("contributors") + "?limit=101").status_code == 400
    assert APIClient().get(entity_path("contributors")).status_code == 403
