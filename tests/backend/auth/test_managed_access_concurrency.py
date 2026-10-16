from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.management_access.policy import AccessConflict
from apps.accounts.management_access.services import (
    create_managed_grant,
    update_managed_account,
)
from django.db import close_old_connections, connections
from rest_framework.exceptions import ValidationError

from .managed_access_fixtures import create_account_pair

pytestmark = pytest.mark.django_db(transaction=True)


def invoke(operation, arguments, barrier):
    close_old_connections()
    try:
        barrier.wait(timeout=10)
        try:
            return operation(*arguments)
        except (AccessConflict, ValidationError):
            return "conflict"
    finally:
        connections.close_all()


def concurrent_calls(operation, arguments):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(invoke, operation, argument, barrier)
            for argument in arguments
        ]
        return [future.result(timeout=15) for future in futures]


def test_concurrent_duplicate_grants_create_one_record():
    actor, target = create_account_pair("duplicate")
    values = {"id": str(uuid4()), "scope": PermissionScope.READ_DURABLE}
    results = concurrent_calls(create_managed_grant, [(actor, target.pk, values)] * 2)
    assert results[0].pk == results[1].pk
    assert PermissionGrant.objects.filter(user=target).count() == 1


def test_concurrent_opposing_grants_do_not_create_conflicting_read_access():
    actor, target = create_account_pair("opposing")
    arguments = [
        (actor, target.pk, {"id": str(uuid4()), "scope": scope})
        for scope in (PermissionScope.READ_ONCE, PermissionScope.READ_DURABLE)
    ]
    results = concurrent_calls(create_managed_grant, arguments)
    assert results.count("conflict") == 1
    assert PermissionGrant.objects.filter(user=target).count() == 1


def test_concurrent_account_revisions_accept_only_one_update():
    actor, target = create_account_pair("revision")
    arguments = [
        (
            actor,
            target.pk,
            {"expected_updated_at": target.updated_at.isoformat(), "full_name": name},
        )
        for name in ("প্রথম নাম", "দ্বিতীয় নাম")
    ]
    results = concurrent_calls(update_managed_account, arguments)
    assert results.count("conflict") == 1


def test_cross_account_uuid_collision_returns_a_conflict():
    first, second = create_account_pair("first"), create_account_pair("second")
    values = {"id": str(uuid4()), "scope": PermissionScope.SEND_KINDLE}
    results = concurrent_calls(
        create_managed_grant,
        [(actor, target.pk, values) for actor, target in (first, second)],
    )
    assert results.count("conflict") == 1
    assert (
        PermissionGrant.objects.filter(scope=PermissionScope.SEND_KINDLE).count() == 1
    )
