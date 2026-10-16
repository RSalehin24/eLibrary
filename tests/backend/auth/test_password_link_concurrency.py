from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from apps.accounts.models import User
from apps.accounts.password_links import confirm_password_link
from django.db import close_old_connections, connections
from rest_framework.exceptions import ValidationError

from .password_link_fixtures import confirmation_values

pytestmark = pytest.mark.django_db(transaction=True)


def confirm_at_barrier(values, barrier):
    close_old_connections()
    try:
        barrier.wait(timeout=10)
        try:
            return confirm_password_link(values).pk
        except ValidationError as error:
            if "token" not in error.detail:
                raise
            return "invalid"
    finally:
        connections.close_all()


def test_concurrent_password_link_confirmation_consumes_the_link_once():
    user = User.objects.create_user(
        email="password-link-race@library.test", email_setup_pending=True
    )
    values = confirmation_values(user)
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(confirm_at_barrier, values, barrier) for _ in range(2)
        ]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(results, key=str) == sorted([user.pk, "invalid"], key=str)
    user.refresh_from_db()
    assert user.password_setup_nonce == 1 and not user.email_setup_pending
