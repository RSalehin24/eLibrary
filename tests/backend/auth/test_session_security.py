import pytest
from apps.accounts.models import User
from apps.accounts.session_security import rotate_account_sessions
from django.contrib.auth.base_user import AbstractBaseUser
from django.test import Client
from django_otp.plugins.otp_totp.models import TOTPDevice

pytestmark = pytest.mark.django_db
PASSWORD = "Session-Security-Password-2026"
PROFILE = "/api/v1/auth/profile/"


def test_email_identity_preserves_schema_name_helpers_and_validation(session_account):
    user, _, _ = session_account
    user.first_name, user.last_name = "বাংলা", "পাঠক"
    user.email = "reader@LIBRARY.TEST"
    user.clean()
    assert user.email == "reader@library.test" and user.username is None
    assert user.get_full_name() == "বাংলা পাঠক" and user.get_short_name() == "বাংলা"
    assert not any(field.name == "username" for field in user._meta.get_fields())


@pytest.mark.parametrize("action", ["setup", "confirm", "cancel", "disable"])
def test_security_mutations_recheck_an_account_disabled_after_authentication(
    session_account, security_clock, action
):
    from apps.accounts.security_services import (
        cancel_totp_setup,
        confirm_totp_setup,
        disable_totp,
        start_totp_setup,
    )
    from rest_framework.exceptions import PermissionDenied

    user, _, _ = session_account
    stale = User.objects.get(pk=user.pk)
    device = TOTPDevice.objects.create(user=user, confirmed=action == "disable")
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    operations = {
        "setup": lambda: start_totp_setup(stale, PASSWORD),
        "confirm": lambda: confirm_totp_setup(stale, security_clock.token(device)),
        "cancel": lambda: cancel_totp_setup(stale),
        "disable": lambda: disable_totp(
            stale, {"current_password": PASSWORD, "token": security_clock.token(device)}
        ),
    }
    with pytest.raises(PermissionDenied):
        operations[action]()
    device.refresh_from_db()
    assert (
        device.throttling_failure_count == 0
        and TOTPDevice.objects.filter(user=user).count() == 1
    )


@pytest.fixture
def session_account():
    user = User.objects.create_user(
        email="session-revision@library.test", password=PASSWORD
    )
    current, previous = Client(), Client()
    current.force_login(user)
    previous.force_login(user)
    return user, current, previous


def post(client, action, values):
    return client.post(
        f"/api/v1/auth/2fa/{action}/", values, content_type="application/json"
    )


def confirm_device(account, clock):
    user, current, _ = account
    assert post(current, "setup", {"current_password": PASSWORD}).status_code == 200
    device = TOTPDevice.objects.get(user=user, confirmed=False)
    assert post(current, "confirm", {"token": clock.token(device)}).status_code == 204
    return device


def test_confirming_totp_expires_other_sessions_and_keeps_the_verified_session(
    session_account, security_clock
):
    user, current, previous = session_account
    original_cookie = current.cookies["sessionid"].value
    confirm_device(session_account, security_clock)
    user.refresh_from_db()
    assert (
        user.session_revision == 1
        and current.cookies["sessionid"].value != original_cookie
    )
    assert (
        current.get(PROFILE).status_code == 200
        and previous.get(PROFILE).status_code == 403
    )
    assert current.session["otp_device_id"]


def test_disabling_totp_rotates_sessions_again(session_account, security_clock):
    user, current, _ = session_account
    device = confirm_device(session_account, security_clock)
    other = Client()
    user.refresh_from_db()
    other.force_login(user)
    security_clock.timestamp += device.step
    assert (
        post(
            current,
            "disable",
            {"current_password": PASSWORD, "token": security_clock.token(device)},
        ).status_code
        == 204
    )
    user.refresh_from_db()
    assert user.session_revision == 2 and not user.has_totp_enabled
    assert (
        current.get(PROFILE).status_code == 200
        and other.get(PROFILE).status_code == 403
    )


@pytest.mark.parametrize("field", ["is_active", "totp_required"])
def test_security_policy_changes_cannot_restore_an_old_session_after_reversal(
    session_account, field
):
    user, current, previous = session_account
    initial = getattr(user, field)
    setattr(user, field, not initial)
    user.save(update_fields=[field, "updated_at"])
    setattr(user, field, initial)
    user.save(update_fields=[field, "updated_at"])
    user.refresh_from_db()
    assert user.session_revision == 2
    assert current.get(PROFILE).status_code == previous.get(PROFILE).status_code == 403


def test_ordinary_account_edits_and_unchanged_policy_keep_sessions(session_account):
    user, current, previous = session_account
    user.full_name = "পরিবর্তিত নাম"
    user.save()
    user.save(update_fields=["is_active", "totp_required", "updated_at"])
    assert user.session_revision == 0
    assert current.get(PROFILE).status_code == previous.get(PROFILE).status_code == 200


def test_a_stale_profile_save_cannot_roll_back_the_session_revision(session_account):
    user, current, previous = session_account
    stale = User.objects.get(pk=user.pk)
    rotate_account_sessions(user)
    stale.full_name = "পুরোনো ফর্মের নাম"
    stale.save()
    stale.refresh_from_db()
    assert stale.session_revision == 1
    assert current.get(PROFILE).status_code == previous.get(PROFILE).status_code == 403


def test_unmodified_accounts_keep_django_session_hash_and_secret_rotation(
    session_account, settings
):
    user, current, previous = session_account
    assert user.get_session_auth_hash() == AbstractBaseUser._get_session_auth_hash(user)
    original_secret = settings.SECRET_KEY
    settings.SECRET_KEY = "synthetic-new-test-signing-key"
    settings.SECRET_KEY_FALLBACKS = [original_secret]
    assert current.get(PROFILE).status_code == previous.get(PROFILE).status_code == 200


def test_revised_sessions_support_secret_key_rotation(
    session_account, security_clock, settings
):
    _, current, _ = session_account
    confirm_device(session_account, security_clock)
    original_secret = settings.SECRET_KEY
    settings.SECRET_KEY = "synthetic-rotated-test-signing-key"
    settings.SECRET_KEY_FALLBACKS = [original_secret]
    assert current.get(PROFILE).status_code == 200


def test_failed_totp_confirmation_does_not_expire_sessions(
    session_account, security_clock
):
    user, current, previous = session_account
    assert post(current, "setup", {"current_password": PASSWORD}).status_code == 200
    device = TOTPDevice.objects.get(user=user)
    assert (
        post(
            current, "confirm", {"token": security_clock.incorrect_token(device)}
        ).status_code
        == 400
    )
    user.refresh_from_db()
    assert user.session_revision == 0
    assert current.get(PROFILE).status_code == previous.get(PROFILE).status_code == 200


def test_legacy_confirmation_uses_the_same_session_rotation_and_verified_marker(
    session_account, security_clock
):
    user, current, previous = session_account
    device = TOTPDevice.objects.create(user=user, confirmed=False)
    response = current.post(
        "/api/auth/2fa/confirm/",
        {"token": security_clock.token(device)},
        content_type="application/json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.session_revision == 1 and current.session["otp_device_id"]
    assert (
        current.get(PROFILE).status_code == 200
        and previous.get(PROFILE).status_code == 403
    )


def test_legacy_confirmation_failures_preserve_throttle_counters(
    session_account, security_clock
):
    user, current, _ = session_account
    device = TOTPDevice.objects.create(user=user, confirmed=False)
    response = current.post(
        "/api/auth/2fa/confirm/",
        {"token": security_clock.incorrect_token(device)},
        content_type="application/json",
    )
    assert response.status_code == 400
    device.refresh_from_db()
    assert device.throttling_failure_count == 1


def test_legacy_disable_expires_other_sessions(session_account, security_clock):
    user, current, _ = session_account
    confirm_device(session_account, security_clock)
    user.refresh_from_db()
    other = Client()
    other.force_login(user)
    assert (
        current.post(
            "/api/auth/2fa/disable/", {}, content_type="application/json"
        ).status_code
        == 200
    )
    user.refresh_from_db()
    assert user.session_revision == 2
    assert (
        current.get(PROFILE).status_code == 200
        and other.get(PROFILE).status_code == 403
    )
