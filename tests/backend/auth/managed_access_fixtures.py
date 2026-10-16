from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User

USERS = "/api/v1/manage/users/"
REFERENCES = "/api/v1/manage/access/references/"


def create_account_pair(identity):
    actor = User.objects.create_user(email=f"access-manager-{identity}@library.test")
    target = User.objects.create_user(
        email=f"managed-reader-{identity}@library.test", full_name="বাংলা পাঠক"
    )
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.ACCESS_MANAGE)
    return actor, target


@pytest.fixture
def accounts(client):
    actor, target = create_account_pair("fixture")
    client.force_login(actor)
    return actor, target


def account_url(target):
    return f"{USERS}{target.pk}/"


def grant_request(scope=PermissionScope.READ_DURABLE):
    return {"id": str(uuid4()), "scope": scope, "notes": "পাঠের অনুমতি"}
