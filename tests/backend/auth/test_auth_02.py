import json

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User


@pytest.mark.django_db
def test_totp_required_users_are_limited_to_setup_endpoints_until_configured(client):
    user = User.objects.create_user(
        email="setup-required@example.com",
        password="strong-password-123",
        full_name="Needs Setup",
        totp_required=True,
    )
    client.force_login(user)

    session = client.get("/api/auth/session/")
    assert session.status_code == 200
    assert session.json()["user"]["totp_required"] is True
    assert session.json()["user"]["totp_setup_required"] is True

    status_response = client.get("/api/auth/2fa/status/")
    assert status_response.status_code == 200
    assert status_response.json()["required"] is True
    assert status_response.json()["setup_required"] is True

    blocked = client.get("/api/catalog/books/")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "otp_setup_required"

    setup = client.post(
        "/api/auth/2fa/setup/",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert setup.status_code == 200
    assert setup.json()["provisioning_uri"].startswith("otpauth://")
    assert "RSalehin24%20Library" in setup.json()["provisioning_uri"]
    assert "<svg" in setup.json()["qr_svg"]

    cancel = client.post(
        "/api/auth/2fa/cancel/",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert cancel.status_code == 200

    after_cancel = client.get("/api/auth/2fa/status/")
    assert after_cancel.status_code == 200
    assert after_cancel.json()["pending_setup"] is False
    assert after_cancel.json()["setup_required"] is True

    disable = client.post(
        "/api/auth/2fa/disable/",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert disable.status_code == 400


@pytest.mark.django_db
def test_authenticated_user_can_update_profile_name(client):
    user = User.objects.create_user(
        email="profile@example.com",
        password="strong-password-123",
        full_name="Before",
    )
    client.force_login(user)

    response = client.patch(
        "/api/auth/profile/",
        data=json.dumps({"full_name": "After"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.full_name == "After"


@pytest.mark.django_db
def test_profile_exposes_and_updates_kindle_emails(settings, client):
    settings.ACCOUNT_INVITE_FROM_EMAIL = "library-sender@example.com"
    user = User.objects.create_user(
        email="kindle-profile@example.com",
        password="strong-password-123",
        full_name="Kindle User",
    )
    PermissionGrant.objects.create(user=user, scope=PermissionScope.SEND_KINDLE)
    client.force_login(user)

    response = client.patch(
        "/api/auth/profile/",
        data=json.dumps(
            {
                "kindle_emails_text": "reader@kindle.com\nreader-two@kindle.com\nreader@kindle.com",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.kindle_emails == [
        "reader@kindle.com",
        "reader-two@kindle.com",
    ]
    assert response.json()["kindle_emails"] == user.kindle_emails
    assert response.json()["kindle_sender_email"] == "library-sender@example.com"


@pytest.mark.django_db
def test_profile_rejects_non_kindle_email_addresses(client):
    user = User.objects.create_user(
        email="kindle-profile-invalid@example.com",
        password="strong-password-123",
        full_name="Kindle User",
    )
    PermissionGrant.objects.create(user=user, scope=PermissionScope.SEND_KINDLE)
    client.force_login(user)

    response = client.patch(
        "/api/auth/profile/",
        data=json.dumps(
            {
                "kindle_emails_text": "reader@example.com",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["kindle_emails"] == [
        "Enter a Kindle email ending in @kindle.com."
    ]


@pytest.mark.django_db
def test_authenticated_user_can_upload_profile_image(client):
    user = User.objects.create_user(
        email="photo@example.com",
        password="strong-password-123",
        full_name="Photo User",
    )
    api_client = APIClient()
    api_client.force_authenticate(user=user)

    upload = SimpleUploadedFile("avatar.png", b"fake-image-bytes", content_type="image/png")

    response = api_client.patch(
        "/api/auth/profile/",
        data={"full_name": "Photo User", "profile_image": upload},
        format="multipart",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert bool(user.profile_image.name) is True
    assert response.json()["profile_image_url"]


@pytest.mark.django_db
def test_authenticated_user_can_change_password_from_profile_and_remain_signed_in(client):
    user = User.objects.create_user(
        email="password-change@example.com",
        password="strong-password-123",
        full_name="Password User",
    )
    client.force_login(user)

    response = client.patch(
        "/api/auth/profile/",
        data=json.dumps(
            {
                "current_password": "strong-password-123",
                "new_password": "strong-password-456",
                "confirm_new_password": "strong-password-456",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("strong-password-456") is True

    session_response = client.get("/api/auth/session/")
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True


@pytest.mark.django_db
def test_profile_password_change_requires_the_current_password(client):
    user = User.objects.create_user(
        email="password-guard@example.com",
        password="strong-password-123",
        full_name="Password Guard",
    )
    client.force_login(user)

    response = client.patch(
        "/api/auth/profile/",
        data=json.dumps(
            {
                "current_password": "wrong-password-123",
                "new_password": "strong-password-456",
                "confirm_new_password": "strong-password-456",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "current_password" in response.json()
    user.refresh_from_db()
    assert user.check_password("strong-password-123") is True
