import pytest
from apps.accounts.models import User
from django.test import Client
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
SECURITY_URL = "/api/v1/auth/2fa/"
PASSWORD = "Reader-Security-Password-2026"


@pytest.fixture
def security_account():
    user = User.objects.create_user(email="security@library.test", password=PASSWORD)
    client = APIClient()
    client.force_authenticate(user)
    return client, user


def post(client, action, values=None):
    return client.post(f"{SECURITY_URL}{action}/", values or {}, format="json")


def pending_device(account):
    client, user = account
    assert post(client, "setup", {"current_password": PASSWORD}).status_code == 200
    return TOTPDevice.objects.get(user=user, confirmed=False)


def test_security_endpoints_require_authentication_and_prohibit_caching(
    security_account,
):
    client, _ = security_account
    assert APIClient().get(f"{SECURITY_URL}status/").status_code == 403
    for action in ["setup", "confirm", "cancel", "disable"]:
        assert post(APIClient(), action).status_code == 403
    status = client.get(f"{SECURITY_URL}status/")
    assert status.json() == {
        "enabled": False,
        "pending_setup": False,
        "required": False,
        "setup_required": False,
    }
    assert status["Cache-Control"] == "private, no-store"
    assert status["X-Robots-Tag"] == "noindex"


def test_setup_reauthenticates_and_reuses_an_interrupted_setup(security_account):
    client, user = security_account
    rejected = post(client, "setup", {"current_password": "incorrect"})
    assert (
        rejected.status_code == 400
        and "current_password" in rejected.json()["field_errors"]
    )
    assert not TOTPDevice.objects.filter(user=user).exists()
    setup = post(client, "setup", {"current_password": PASSWORD})
    resumed = post(client, "setup", {"current_password": PASSWORD})
    assert setup.status_code == 200 and setup.json() == resumed.json()
    assert setup.json()["secret"] and setup.json()["provisioning_uri"].startswith(
        "otpauth://totp/"
    )
    assert "<svg" in setup.json()["qr_svg"]
    assert TOTPDevice.objects.filter(user=user).count() == 1
    assert setup["Cache-Control"] == "private, no-store"


def test_failed_confirmation_persists_throttling(security_account, security_clock):
    client, _ = security_account
    device = pending_device(security_account)
    assert (
        post(
            client, "confirm", {"token": security_clock.incorrect_token(device)}
        ).status_code
        == 400
    )
    device.refresh_from_db()
    assert device.throttling_failure_count == 1 and not device.confirmed
    assert (
        post(client, "confirm", {"token": security_clock.token(device)}).status_code
        == 400
    )
    security_clock.timestamp += 2
    assert (
        post(client, "confirm", {"token": security_clock.token(device)}).status_code
        == 204
    )
    device.refresh_from_db()
    assert device.confirmed and device.throttling_failure_count == 0
    assert (
        post(client, "confirm", {"token": security_clock.token(device)}).status_code
        == 400
    )
    assert post(client, "setup", {"current_password": PASSWORD}).status_code == 400


def test_disabling_requires_password_and_fresh_nonreplayed_code(
    security_account, security_clock
):
    client, user = security_account
    device = pending_device(security_account)
    used_code = security_clock.token(device)
    assert post(client, "confirm", {"token": used_code}).status_code == 204
    values = {"current_password": "incorrect", "token": used_code}
    assert post(client, "disable", values).status_code == 400
    values["current_password"] = PASSWORD
    assert post(client, "disable", values).status_code == 400
    device.refresh_from_db()
    assert device.throttling_failure_count == 1
    security_clock.timestamp += device.step
    values["token"] = security_clock.token(device)
    assert post(client, "disable", values).status_code == 204
    assert not TOTPDevice.objects.filter(user=user).exists()


def test_cancel_removes_only_the_accounts_unconfirmed_device(security_account):
    client, user = security_account
    pending_device(security_account)
    confirmed = TOTPDevice.objects.create(user=user, confirmed=True)
    other = User.objects.create_user(email="other-security@library.test")
    private = TOTPDevice.objects.create(user=other, confirmed=False)
    assert post(client, "cancel").status_code == 204
    assert post(client, "cancel").status_code == 204
    assert set(TOTPDevice.objects.values_list("pk", flat=True)) == {
        confirmed.pk,
        private.pk,
    }


def test_required_setup_unblocks_private_work_and_cannot_be_disabled(
    security_account, security_clock
):
    _, user = security_account
    user.totp_required = True
    user.email_setup_pending = True
    user.save()
    client = APIClient()
    client.force_login(user)
    assert client.get("/api/v1/me/books/").json()["code"] == "otp_setup_required"
    device = pending_device((client, user))
    assert (
        post(client, "confirm", {"token": security_clock.token(device)}).status_code
        == 204
    )
    assert client.get("/api/v1/me/books/").status_code == 200
    user.refresh_from_db()
    assert not user.email_setup_pending
    security_clock.timestamp += device.step
    denied = post(
        client,
        "disable",
        {"current_password": PASSWORD, "token": security_clock.token(device)},
    )
    assert denied.status_code == 400
    assert TOTPDevice.objects.filter(user=user, confirmed=True).exists()


@pytest.mark.parametrize(
    "token", ["12345", "1234567", "abcdef", "１２３４５６", "123456789"]
)
def test_confirmation_rejects_invalid_code_shapes(security_account, token):
    client, _ = security_account
    device = pending_device(security_account)
    assert post(client, "confirm", {"token": token}).status_code == 400
    device.refresh_from_db()
    assert device.throttling_failure_count == 0 and not device.confirmed


@pytest.mark.parametrize("action", ["setup", "confirm", "cancel", "disable"])
def test_security_commands_enforce_real_session_csrf(security_account, action):
    _, user = security_account
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    csrf = client.get("/api/v1/auth/session/").json()["csrf_token"]
    url = f"{SECURITY_URL}{action}/"
    assert client.post(url, {}, content_type="application/json").status_code == 403
    assert (
        client.post(
            url, {}, content_type="application/json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        != 403
    )


def test_eight_digit_devices_remain_supported(security_account, security_clock):
    client, user = security_account
    device = pending_device(security_account)
    device.digits = 8
    device.save(update_fields=["digits"])
    code = security_clock.token(device)
    assert len(code) == 8
    assert post(client, "confirm", {"token": code}).status_code == 204
    security_clock.timestamp += device.step
    login = APIClient()
    csrf = login.get("/api/v1/auth/session/").json()["csrf_token"]
    response = login.post(
        "/api/v1/auth/login/",
        {
            "email": user.email,
            "password": PASSWORD,
            "otp_token": security_clock.token(device),
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
