from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from apps.accounts.models import User
from django.contrib.auth import SESSION_KEY
from django.db import close_old_connections, connections
from django.test import Client
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = "Maintenance-OTP-Password-2026"


def maintenance_account():
    return User.objects.create_user(
        email="maintenance@library.test",
        password=PASSWORD,
        is_staff=True,
        totp_required=False,
    )


def test_enabled_two_factor_cannot_be_bypassed_by_the_maintenance_password_form():
    user = maintenance_account()
    TOTPDevice.objects.create(user=user, confirmed=True)
    client = Client()
    response = client.post(
        "/admin/login/",
        {"username": user.email, "password": PASSWORD, "next": "/admin/"},
    )
    assert response.status_code == 200
    assert SESSION_KEY not in client.session
    device = TOTPDevice.objects.get(user=user)
    assert device.throttling_failure_count == 0
    assert b'name="otp_challenge"' not in response.content


def test_required_setup_cannot_be_bypassed_by_a_password_only_staff_session():
    user = maintenance_account()
    user.totp_required = True
    user.save()
    client = Client()
    client.force_login(user)
    assert client.get("/admin/").status_code == 302


def test_optional_two_factor_keeps_staff_maintenance_access_without_a_device():
    user = maintenance_account()
    client = Client()
    client.force_login(user)
    assert client.get("/admin/").status_code == 200


def test_maintenance_accepts_one_fresh_code_and_rejects_replay(security_clock):
    user = maintenance_account()
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    fields = {
        "username": user.email,
        "password": PASSWORD,
        "otp_token": security_clock.token(device),
        "next": "/admin/",
    }
    client = Client()
    assert client.post("/admin/login/", fields).status_code == 302
    assert client.session[DEVICE_ID_SESSION_KEY] == device.persistent_id
    assert client.get("/admin/").status_code == 200
    other = Client()
    assert other.post("/admin/login/", fields).status_code == 200
    assert SESSION_KEY not in other.session


@pytest.mark.parametrize("path", ["/api/v1/auth/login/", "/api/auth/login/"])
def test_library_login_persists_the_verified_device_for_maintenance(
    path, security_clock
):
    user = maintenance_account()
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    client = APIClient(REMOTE_ADDR="192.0.2.31")
    csrf = client.get("/api/v1/auth/session/").json()["csrf_token"]
    response = client.post(
        path,
        {
            "email": user.email,
            "password": PASSWORD,
            "otp_token": security_clock.token(device),
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    assert client.session[DEVICE_ID_SESSION_KEY] == device.persistent_id
    assert client.get("/admin/").status_code == 200


def test_setup_confirmation_marks_the_current_session_and_blocks_unconfirmed_sessions(
    security_clock,
):
    user = maintenance_account()
    user.totp_required = True
    user.save()
    device = TOTPDevice.objects.create(user=user, confirmed=False)
    client = APIClient()
    client.force_login(user)
    other = Client()
    other.force_login(user)
    csrf = client.get("/api/v1/auth/session/").json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/2fa/confirm/",
        {"token": security_clock.token(device)},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 204
    assert client.session[DEVICE_ID_SESSION_KEY] == device.persistent_id
    assert client.get("/admin/").status_code == 200
    assert other.get("/admin/").status_code == 302
    device.confirmed = False
    device.save()
    assert client.get("/admin/").status_code == 302


def test_invalid_maintenance_codes_commit_the_throttle_counter(security_clock):
    user = maintenance_account()
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    client = Client()
    response = client.post(
        "/admin/login/",
        {
            "username": user.email,
            "password": PASSWORD,
            "otp_token": security_clock.incorrect_token(device),
            "next": "/admin/",
        },
    )
    assert response.status_code == 200
    device.refresh_from_db()
    assert device.throttling_failure_count == 1
    assert SESSION_KEY not in client.session


def test_reader_with_a_verified_code_does_not_receive_staff_maintenance_access(
    security_clock,
):
    user = maintenance_account()
    user.is_staff = False
    user.save()
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    client = Client()
    response = client.post(
        "/admin/login/",
        {
            "username": user.email,
            "password": PASSWORD,
            "otp_token": security_clock.token(device),
            "next": "/admin/",
        },
    )
    assert response.status_code == 200
    assert SESSION_KEY not in client.session


def test_maintenance_login_enforces_csrf_before_consuming_the_code(security_clock):
    user = maintenance_account()
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    client = Client(enforce_csrf_checks=True)
    fields = {
        "username": user.email,
        "password": PASSWORD,
        "otp_token": security_clock.token(device),
        "next": "/admin/",
    }
    assert client.post("/admin/login/", fields).status_code == 403
    client.get("/admin/login/")
    csrf = client.cookies["csrftoken"].value
    assert (
        client.post("/admin/login/", fields, HTTP_X_CSRFTOKEN=csrf).status_code == 302
    )


def test_maintenance_rejects_a_device_session_bound_to_another_account():
    user = maintenance_account()
    TOTPDevice.objects.create(user=user, confirmed=True)
    other = User.objects.create_user(email="other-maintenance@library.test")
    private_device = TOTPDevice.objects.create(user=other, confirmed=True)
    client = Client()
    client.force_login(user)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = private_device.persistent_id
    session.save()
    assert client.get("/admin/").status_code == 302
    assert DEVICE_ID_SESSION_KEY not in client.session


def concurrent_login(path, fields, barrier):
    close_old_connections()
    try:
        client = APIClient(enforce_csrf_checks=True, REMOTE_ADDR="192.0.2.41")
        csrf = client.get("/api/v1/auth/session/").json()["csrf_token"]
        barrier.wait(timeout=10)
        if path == "/admin/login/":
            client.post(
                path,
                {**fields, "username": fields["email"], "next": "/admin/"},
                HTTP_X_CSRFTOKEN=csrf,
            )
        else:
            client.post(path, fields, format="json", HTTP_X_CSRFTOKEN=csrf)
        return SESSION_KEY in client.session
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_maintenance_and_library_login_cannot_accept_the_same_code_concurrently(
    security_clock,
):
    user = maintenance_account()
    device = TOTPDevice.objects.create(user=user, confirmed=True)
    fields = {
        "email": user.email,
        "password": PASSWORD,
        "otp_token": security_clock.token(device),
    }
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(concurrent_login, path, fields, barrier)
            for path in ["/admin/login/", "/api/v1/auth/login/"]
        ]
        assert sorted(future.result(timeout=15) for future in futures) == [False, True]
