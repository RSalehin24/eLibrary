from uuid import uuid4

from apps.accounts.models import User
from rest_framework.test import APIClient


def entity_client():
    actor = User.objects.create_user(email=f"{uuid4()}@entities.test", is_staff=True)
    client = APIClient()
    client.force_authenticate(actor)
    return actor, client


def entity_path(kind, identifier=None):
    base = f"/api/v1/manage/entities/{kind}/"
    return base if identifier is None else f"{base}{identifier}/"


def create_entity_response(client, kind="contributors", **values):
    return client.post(
        entity_path(kind),
        {"operation_id": str(uuid4()), "name": "নতুন পরিচিতি", **values},
        format="json",
    )


def entity_revision(data, **values):
    return {"expected_updated_at": data["updated_at"], **values}
