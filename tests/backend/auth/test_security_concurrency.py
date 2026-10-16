from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
from apps.accounts.models import User
from django.db import close_old_connections, connections
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db(transaction=True)
PASSWORD = "Concurrent-Authenticator-Password-2026"


def submit_at_barrier(user, command, barrier):
    close_old_connections()
    try:
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        csrf = client.get("/api/v1/auth/session/").json()["csrf_token"]
        barrier.wait(timeout=10)
        response = client.post(
            command[0], command[1], format="json", HTTP_X_CSRFTOKEN=csrf
        )
        return (
            response.status_code,
            response.json() if response.status_code == 200 else None,
        )
    finally:
        connections.close_all()


def concurrent_responses(user, command):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(submit_at_barrier, user, command, barrier) for _ in range(2)
        ]
        return [future.result(timeout=15) for future in futures]


def test_concurrent_setup_creates_one_secret():
    user = User.objects.create_user(email="setup-race@library.test", password=PASSWORD)
    command = ("/api/v1/auth/2fa/setup/", {"current_password": PASSWORD})
    results = concurrent_responses(user, command)
    assert [status for status, _ in results] == [200, 200]
    assert results[0][1] == results[1][1]
    assert TOTPDevice.objects.filter(user=user).count() == 1


def test_concurrent_confirmation_consumes_the_code_once(monkeypatch):
    user = User.objects.create_user(
        email="confirmation-race@library.test", password=PASSWORD
    )
    device = TOTPDevice.objects.create(user=user, confirmed=False)
    timestamp = 1791936000
    monkeypatch.setattr(
        "django_otp.plugins.otp_totp.models.time",
        SimpleNamespace(time=lambda: timestamp),
    )
    authenticator = TOTP(
        device.bin_key, device.step, device.t0, device.digits, device.drift
    )
    authenticator.time = timestamp
    token = str(authenticator.token()).zfill(device.digits)
    results = concurrent_responses(
        user, ("/api/v1/auth/2fa/confirm/", {"token": token})
    )
    assert sorted(status for status, _ in results) == [204, 400]
    device.refresh_from_db()
    assert device.confirmed and device.last_t == authenticator.t()


@pytest.mark.parametrize("other_path", ["/api/auth/login/", "/api/v1/auth/login/"])
def test_parallel_login_paths_cannot_reuse_a_confirmed_code(monkeypatch, other_path):
    user = User.objects.create_user(email="login-race@library.test", password=PASSWORD)
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    timestamp = 1791936000
    monkeypatch.setattr(
        "django_otp.plugins.otp_totp.models.time",
        SimpleNamespace(time=lambda: timestamp),
    )
    authenticator = TOTP(
        device.bin_key, device.step, device.t0, device.digits, device.drift
    )
    authenticator.time = timestamp
    token = str(authenticator.token()).zfill(device.digits)
    barrier = Barrier(2)
    values = {"email": user.email, "password": PASSWORD, "otp_token": token}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(submit_at_barrier, None, (path, values), barrier)
            for path in ["/api/v1/auth/login/", other_path]
        ]
        results = [future.result(timeout=15) for future in futures]
    assert sorted(status for status, _ in results) == [200, 400]
