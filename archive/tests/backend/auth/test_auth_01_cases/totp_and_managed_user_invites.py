import json
import re
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.accounts.serializers.support import (
    PasswordLinkTokenGenerator,
    password_link_token_generator,
)


def extract_password_link_params(message_body, path):
    match = re.search(
        rf"https?://[^ ]+{re.escape(path)}\?uid=[^ \n]+&token=[^ \n]+",
        message_body,
    )
    assert match is not None
    parsed = urlparse(match.group(0))
    params = parse_qs(parsed.query)
    return params["uid"][0], params["token"][0]


def extract_setup_link_params(message_body):
    return extract_password_link_params(message_body, "/create-password")


def extract_reset_link_params(message_body):
    return extract_password_link_params(message_body, "/reset-password/confirm")


def build_totp_token(device):
    return str(
        totp(
            device.bin_key,
            step=device.step,
            t0=device.t0,
            digits=device.digits,
            drift=device.drift,
        )
    ).zfill(device.digits)


@pytest.mark.django_db
def test_email_login_requires_totp_when_enabled(client):
    user = User.objects.create_user(
        email="reader@example.com",
        password="strong-password-123",
        full_name="Reader",
    )

    response = client.post(
        "/api/auth/login/",
        data=json.dumps({"email": user.email, "password": "strong-password-123"}),
        content_type="application/json",
    )
    assert response.status_code == 200

    client.post("/api/auth/logout/")

    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    missing_token = client.post(
        "/api/auth/login/",
        data=json.dumps({"email": user.email, "password": "strong-password-123"}),
        content_type="application/json",
    )
    assert missing_token.status_code == 400
    assert missing_token.json()["code"] == "otp_required"

    token = build_totp_token(device)
    valid_token = client.post(
        "/api/auth/login/",
        data=json.dumps(
            {
                "email": user.email,
                "password": "strong-password-123",
                "otp_token": token,
            }
        ),
        content_type="application/json",
    )
    assert valid_token.status_code == 200
    assert valid_token.json()["email"] == user.email


@pytest.mark.django_db
def test_only_superadmin_can_create_managed_users(client):
    superadmin = User.objects.create_superuser(
        email="superadmin@example.com",
        password="strong-password-123",
    )
    regular_user = User.objects.create_user(
        email="member@example.com",
        password="strong-password-123",
    )

    client.force_login(regular_user)
    denied = client.post(
        "/api/auth/users/",
        data=json.dumps(
            {
                "email": "created@example.com",
                "full_name": "Created User",
                "password": "strong-password-456",
                "is_active": True,
            }
        ),
        content_type="application/json",
    )
    assert denied.status_code == 403

    client.force_login(superadmin)
    created = client.post(
        "/api/auth/users/",
        data=json.dumps(
            {
                "email": "created@example.com",
                "full_name": "Created User",
                "password": "strong-password-456",
                "is_active": True,
                "global_scopes": ["read:durable"],
            }
        ),
        content_type="application/json",
    )
    assert created.status_code == 201
    assert User.objects.filter(email="created@example.com", is_superuser=False, is_staff=False).exists()


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://127.0.0.1:5173",
    FRONTEND_PORT="5173",
)
def test_superadmin_can_create_managed_user_and_send_invite_email(client):
    superadmin = User.objects.create_superuser(
        email="superadmin@example.com",
        password="strong-password-123",
        full_name="Super Admin",
    )
    client.force_login(superadmin)

    created = client.post(
        "/api/auth/users/",
        data=json.dumps(
            {
                "email": "invited@example.com",
                "full_name": "Invited User",
                "is_active": True,
                "send_invite_email": True,
                "global_scopes": ["read:durable"],
            }
        ),
        content_type="application/json",
    )

    assert created.status_code == 201
    invited_user = User.objects.get(email="invited@example.com")
    assert invited_user.check_password("") is False
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["invited@example.com"]
    assert "Your RSalehin24 Library account is ready" in mail.outbox[0].subject
    assert "http://127.0.0.1:5173/create-password?uid=" in mail.outbox[0].body
    assert "&amp;" not in mail.outbox[0].body

    html_body, html_mimetype = mail.outbox[0].alternatives[0]
    assert html_mimetype == "text/html"
    assert "display: block;" in html_body
    assert "width: 100%;" in html_body
    assert "font-size: 18px" in html_body


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://localhost",
    FRONTEND_PORT="5173",
)
def test_invite_email_uses_frontend_port_when_frontend_base_url_omits_it(client):
    superadmin = User.objects.create_superuser(
        email="port-superadmin@example.com",
        password="strong-password-123",
        full_name="Super Admin",
    )
    client.force_login(superadmin)

    created = client.post(
        "/api/auth/users/",
        data=json.dumps(
            {
                "email": "port-invited@example.com",
                "full_name": "Invited User",
                "is_active": True,
                "send_invite_email": True,
                "global_scopes": ["read:durable"],
            }
        ),
        content_type="application/json",
    )

    assert created.status_code == 201
    assert len(mail.outbox) == 1
    assert "&amp;" not in mail.outbox[0].body

    reset_link_match = re.search(
        r"http://localhost:5173/create-password\?uid=[^ \n]+&token=[^ \n]+",
        mail.outbox[0].body,
    )
    assert reset_link_match is not None

    html_body, html_mimetype = mail.outbox[0].alternatives[0]
    assert html_mimetype == "text/html"
    assert "This is an automated message from localhost:5173." in html_body
