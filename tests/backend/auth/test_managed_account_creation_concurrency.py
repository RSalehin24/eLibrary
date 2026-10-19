import pytest
from apps.accounts.management_access.creation import create_managed_account
from apps.accounts.models import User
from apps.common.models import AuditLog

from .test_managed_access_concurrency import concurrent_calls
from .test_managed_account_creation import creation_values

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_direct_creation_preserves_one_account_and_receipt():
    actor = User.objects.create_superuser(
        email="direct-race@library.test", password="administrator-password"
    )
    values = creation_values()
    results = concurrent_calls(create_managed_account, [(actor, values)] * 2)
    assert results[0].pk == results[1].pk
    assert User.objects.count() == 2 and AuditLog.objects.count() == 1


def test_cross_administrator_operation_collision_is_atomic():
    actors = [
        User.objects.create_superuser(
            email=f"collision-{number}@library.test", password="administrator-password"
        )
        for number in range(2)
    ]
    values = creation_values()
    arguments = [
        (actor, {**values, "email": f"new-{number}@library.test"})
        for number, actor in enumerate(actors)
    ]
    results = concurrent_calls(create_managed_account, arguments)
    assert results.count("conflict") == 1
    assert User.objects.count() == 3 and AuditLog.objects.count() == 1
