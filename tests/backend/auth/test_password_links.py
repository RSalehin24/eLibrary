from datetime import timedelta

import pytest
from apps.accounts.models import User
from apps.accounts.serializers.support import password_link_token_generator
from django.core.cache import cache
from django.test import Client
from django_otp.plugins.otp_totp.models import TOTPDevice

from .password_link_fixtures import (
    CONFIRM,
    INSPECT,
    confirmation_values,
    password_ticket,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_password_link_rate_limit():
    cache.delete("throttle_password_link_127.0.0.1")
    yield
    cache.delete("throttle_password_link_127.0.0.1")


@pytest.fixture
def ticket_user():
    return User.objects.create_user(
        email="password-links@library.test", password="Previous-password-37!safe"
    )


def test_link_inspection_returns_only_the_required_next_steps(client, ticket_user):
    response = client.post(
        INSPECT, password_ticket(ticket_user), content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json() == {"purpose": "reset", "totp_setup_required": False}
    assert (
        response["Cache-Control"] == "private, no-store"
        and response["X-Robots-Tag"] == "noindex"
    )


def test_password_confirmation_consumes_the_link_and_invalidates_existing_sessions(
    client, ticket_user
):
    previous = Client()
    previous.force_login(ticket_user)
    values = confirmation_values(ticket_user)
    response = client.post(CONFIRM, values, content_type="application/json")
    assert response.status_code == 200 and response.json() == {"next_step": "login"}
    ticket_user.refresh_from_db()
    assert ticket_user.check_password(values["new_password"])
    assert ticket_user.password_setup_nonce == 1
    assert previous.get("/api/v1/auth/session/").json()["authenticated"] is False
    assert (
        client.post(CONFIRM, values, content_type="application/json").status_code == 400
    )


def test_invited_account_with_required_totp_receives_a_restricted_setup_session(client):
    user = User.objects.create_user(
        email="required-link@library.test", email_setup_pending=True, totp_required=True
    )
    assert client.post(
        INSPECT, password_ticket(user), content_type="application/json"
    ).json() == {"purpose": "setup", "totp_setup_required": True}
    response = client.post(
        CONFIRM, confirmation_values(user), content_type="application/json"
    )
    assert response.status_code == 200 and response.json() == {
        "next_step": "totp_setup"
    }
    user.refresh_from_db()
    assert user.email_setup_pending is True
    session = client.get("/api/v1/auth/session/").json()
    assert (
        session["authenticated"] is True
        and session["user"]["totp_setup_required"] is True
    )
    assert client.get("/api/v1/me/books/").json()["code"] == "otp_setup_required"


def test_optional_invitation_completes_setup_without_a_session(client):
    user = User.objects.create_user(
        email="optional-link@library.test", email_setup_pending=True
    )
    values = confirmation_values(user)
    assert client.post(CONFIRM, values, content_type="application/json").json() == {
        "next_step": "login"
    }
    user.refresh_from_db()
    assert not user.email_setup_pending and user.has_usable_password()
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False


def test_existing_totp_device_is_preserved_and_cannot_be_bypassed_by_password_reset(
    client, ticket_user
):
    device = TOTPDevice.objects.create(user=ticket_user, confirmed=True)
    values = confirmation_values(ticket_user)
    assert client.post(CONFIRM, values, content_type="application/json").json() == {
        "next_step": "login"
    }
    assert TOTPDevice.objects.filter(pk=device.pk, confirmed=True).exists()
    assert client.get("/api/v1/auth/session/").json()["authenticated"] is False
    response = client.post(
        "/api/v1/auth/login/",
        {"email": ticket_user.email, "password": values["new_password"]},
        content_type="application/json",
    )
    assert response.status_code == 400 and response.json()["code"] == "otp_required"


@pytest.mark.parametrize(
    "uid",
    [
        "broken!",
        "LTE",
        "",
        "YQ",
        "////",
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAw",
    ],
)
def test_invalid_user_identifiers_fail_without_a_server_error(client, uid):
    response = client.post(
        INSPECT, {"uid": uid, "token": "invalid-token"}, content_type="application/json"
    )
    assert response.status_code == 400


def test_disabled_accounts_and_invalid_tokens_receive_the_same_link_error(
    client, ticket_user
):
    values = password_ticket(ticket_user)
    invalid = client.post(
        INSPECT, {**values, "token": "invalid"}, content_type="application/json"
    )
    ticket_user.is_active = False
    ticket_user.save()
    disabled = client.post(INSPECT, values, content_type="application/json")
    assert invalid.status_code == disabled.status_code == 400
    assert invalid.json() == disabled.json()


def test_superseded_links_and_expired_links_cannot_change_passwords(
    client, ticket_user
):
    values = confirmation_values(ticket_user)
    ticket_user.password_setup_nonce += 1
    ticket_user.save()
    assert (
        client.post(CONFIRM, values, content_type="application/json").status_code == 400
    )
    now = password_link_token_generator._now()
    token = password_link_token_generator._make_token_with_timestamp(
        ticket_user,
        password_link_token_generator._num_seconds(now - timedelta(hours=7)),
        password_link_token_generator.secret,
    )
    values = {**confirmation_values(ticket_user), "token": token}
    assert (
        client.post(CONFIRM, values, content_type="application/json").status_code == 400
    )


@pytest.mark.parametrize("password", ["short", "123456789012", "password12345"])
def test_password_length_and_django_password_validators_are_enforced(
    client, ticket_user, password
):
    values = {
        **confirmation_values(ticket_user),
        "new_password": password,
        "confirm_new_password": password,
    }
    response = client.post(CONFIRM, values, content_type="application/json")
    assert (
        response.status_code == 400
        and "new_password" in response.json()["field_errors"]
    )


def test_mismatched_password_confirmation_does_not_consume_the_link(
    client, ticket_user
):
    values = {
        **confirmation_values(ticket_user),
        "confirm_new_password": "Another-safe-password-32!",
    }
    response = client.post(CONFIRM, values, content_type="application/json")
    assert (
        response.status_code == 400
        and "confirm_new_password" in response.json()["field_errors"]
    )
    assert (
        client.post(
            INSPECT, password_ticket(ticket_user), content_type="application/json"
        ).status_code
        == 200
    )


def test_authenticated_accounts_must_sign_out_before_using_a_link(client, ticket_user):
    client.force_login(ticket_user)
    values = confirmation_values(ticket_user)
    assert (
        client.post(INSPECT, values, content_type="application/json").status_code == 400
    )
    assert (
        client.post(CONFIRM, values, content_type="application/json").status_code == 400
    )
    ticket_user.refresh_from_db()
    assert ticket_user.password_setup_nonce == 0


def test_both_anonymous_link_commands_enforce_real_csrf(ticket_user):
    client = Client(enforce_csrf_checks=True)
    values = confirmation_values(ticket_user)
    assert (
        client.post(INSPECT, values, content_type="application/json").status_code == 403
    )
    assert (
        client.post(CONFIRM, values, content_type="application/json").status_code == 403
    )
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    assert (
        client.post(
            INSPECT,
            password_ticket(ticket_user),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )
    assert (
        client.post(
            CONFIRM, values, content_type="application/json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )


def test_link_inspection_is_rate_limited_without_weakening_password_reset_limits(
    client, ticket_user
):
    for _ in range(20):
        assert (
            client.post(
                INSPECT, password_ticket(ticket_user), content_type="application/json"
            ).status_code
            == 200
        )
    response = client.post(
        INSPECT, password_ticket(ticket_user), content_type="application/json"
    )
    assert response.status_code == 429 and response.json()["code"] == "throttled"
    assert "Retry-After" in response


def test_unknown_confirmation_fields_are_rejected_before_consuming_the_link(
    client, ticket_user
):
    values = {**confirmation_values(ticket_user), "is_staff": True}
    response = client.post(CONFIRM, values, content_type="application/json")
    assert response.status_code == 400 and "is_staff" in response.json()["field_errors"]
    ticket_user.refresh_from_db()
    assert ticket_user.password_setup_nonce == 0 and not ticket_user.is_staff


def test_passwords_with_literal_spaces_can_be_used_at_workspace_login(
    client, ticket_user
):
    values = confirmation_values(ticket_user)
    values["new_password"] = values["confirm_new_password"] = (
        "  " + values["new_password"] + "  "
    )
    assert (
        client.post(CONFIRM, values, content_type="application/json").status_code == 200
    )
    response = client.post(
        "/api/v1/auth/login/",
        {"email": ticket_user.email, "password": values["new_password"]},
        content_type="application/json",
        REMOTE_ADDR="127.0.0.87",
    )
    assert response.status_code == 200
