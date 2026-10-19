from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book
from django.utils import timezone

from .managed_access_fixtures import USERS

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "sort,expected",
    [
        ("name_asc", ["A", "b", "c"]),
        ("name_desc", ["c", "b", "A"]),
        ("email_asc", ["c", "b", "A"]),
        ("email_desc", ["A", "b", "c"]),
        ("status", ["A", "c", "b"]),
    ],
)
def test_accounts_restore_all_sorts_with_filters_and_pagination(
    client, accounts, sort, expected
):
    for name, email in [("A", "z"), ("b", "m"), ("c", "a")]:
        User.objects.create_user(
            email=f"sort-{email}@library.test", full_name=name, is_active=name != "b"
        )
    first = client.get(USERS, {"q": "sort-", "sort": sort, "limit": 2}).json()
    second = client.get(
        USERS, {"q": "sort-", "sort": sort, "limit": 2, "page": 2}
    ).json()
    assert [
        entry["full_name"] for entry in first["entries"] + second["entries"]
    ] == expected
    assert first["pagination"]["total_count"] == 3
    active = client.get(USERS, {"q": "sort-", "sort": sort, "status": "active"}).json()
    assert {entry["full_name"] for entry in active["entries"]} == {"A", "c"}


def test_users_search_restores_global_permission_and_status_keywords(client, accounts):
    target = accounts[1]
    PermissionGrant.objects.create(user=target, scope=PermissionScope.SEND_KINDLE)
    expired = User.objects.create_user(email="expired-kindlereader@library.test")
    PermissionGrant.objects.create(
        user=expired,
        scope=PermissionScope.SEND_KINDLE,
        expires_at=timezone.now() - timedelta(days=1),
    )
    scoped = User.objects.create_user(email="scoped-kindlereader@library.test")
    PermissionGrant.objects.create(
        user=scoped,
        scope=PermissionScope.SEND_KINDLE,
        book=Book.objects.create(title="Scoped book"),
    )
    found = client.get(USERS, {"q": "send:kindle"}).json()["entries"]
    assert {entry["id"] for entry in found} == {target.pk}
    assert client.get(USERS, {"q": "required"}).json()["entries"] == []
    target.totp_required = True
    target.save()
    assert [
        entry["id"] for entry in client.get(USERS, {"q": "required"}).json()["entries"]
    ] == [target.pk]


def test_unknown_account_sort_is_rejected(client, accounts):
    response = client.get(USERS, {"sort": "password"})
    assert response.status_code == 400 and "sort" in response.json()["field_errors"]
