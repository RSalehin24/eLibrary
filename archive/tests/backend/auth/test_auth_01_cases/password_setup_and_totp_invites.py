

@pytest.mark.django_db
def test_password_reset_confirm_rejects_reused_token_after_password_is_set(client):
    user = User.objects.create_user(
        email="single-use-link@example.com",
        password="strong-password-123",
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)
    payload = {
        "uid": uid,
        "token": token,
        "new_password": "strong-password-456",
    }

    first_response = client.post(
        "/api/auth/password-reset/confirm/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert first_response.status_code == 200
    assert first_response.json()["next_step"] == "login"

    validate_response = client.post(
        "/api/auth/password-reset/validate/",
        data=json.dumps({"uid": uid, "token": token}),
        content_type="application/json",
    )

    assert validate_response.status_code == 400
    assert validate_response.json()["detail"] == "Reset token is invalid or expired."

    second_response = client.post(
        "/api/auth/password-reset/confirm/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "Reset token is invalid or expired."

    user.refresh_from_db()
    assert user.check_password("strong-password-456") is True


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://127.0.0.1:5173",
    FRONTEND_PORT="5173",
)
def test_resending_setup_email_invalidates_previous_create_password_link(client):
    superadmin = User.objects.create_superuser(
        email="resend-superadmin@example.com",
        password="strong-password-123",
    )
    activation_client = APIClient()
    client.force_login(superadmin)

    created = client.post(
        "/api/auth/users/",
        data=json.dumps(
            {
                "email": "resend-target@example.com",
                "full_name": "Resend Target",
                "is_active": True,
                "send_invite_email": True,
                "global_scopes": ["read:durable"],
            }
        ),
        content_type="application/json",
    )

    assert created.status_code == 201
    assert len(mail.outbox) == 1
    first_uid, first_token = extract_setup_link_params(mail.outbox[0].body)

    invited_user = User.objects.get(email="resend-target@example.com")
    assert invited_user.can_resend_setup_email is True

    resent = client.post(f"/api/auth/users/{invited_user.id}/resend-setup-email/")

    assert resent.status_code == 200
    assert len(mail.outbox) == 2
    second_uid, second_token = extract_setup_link_params(mail.outbox[1].body)
    assert second_uid == first_uid
    assert second_token != first_token

    first_validate = activation_client.post(
        "/api/auth/password-reset/validate/",
        data=json.dumps({"uid": first_uid, "token": first_token}),
        content_type="application/json",
    )

    assert first_validate.status_code == 400
    assert first_validate.json()["detail"] == "Reset token is invalid or expired."

    second_validate = activation_client.post(
        "/api/auth/password-reset/validate/",
        data=json.dumps({"uid": second_uid, "token": second_token}),
        content_type="application/json",
    )

    assert second_validate.status_code == 200
    assert second_validate.json()["detail"] == "Password link is valid."

    first_attempt = activation_client.post(
        "/api/auth/password-reset/confirm/",
        data=json.dumps(
            {
                "uid": first_uid,
                "token": first_token,
                "new_password": "strong-password-456",
            }
        ),
        content_type="application/json",
    )

    assert first_attempt.status_code == 400
    assert first_attempt.json()["detail"] == "Reset token is invalid or expired."

    second_attempt = activation_client.post(
        "/api/auth/password-reset/confirm/",
        data=json.dumps(
            {
                "uid": second_uid,
                "token": second_token,
                "new_password": "strong-password-456",
            }
        ),
        content_type="application/json",
    )

    assert second_attempt.status_code == 200
    assert second_attempt.json()["next_step"] == "login"

    invited_user.refresh_from_db()
    assert invited_user.check_password("strong-password-456") is True
    assert invited_user.email_setup_pending is False


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://127.0.0.1:5173",
    FRONTEND_PORT="5173",
)
def test_totp_required_invite_keeps_setup_resend_available_until_totp_is_confirmed(client):
    superadmin = User.objects.create_superuser(
        email="totp-onboarding-superadmin@example.com",
        password="strong-password-123",
    )
    activation_client = APIClient()
    client.force_login(superadmin)

    created = client.post(
        "/api/auth/users/",
        data=json.dumps(
            {
                "email": "totp-onboarding@example.com",
                "full_name": "TOTP Onboarding",
                "is_active": True,
                "totp_required": True,
                "send_invite_email": True,
                "global_scopes": ["read:durable"],
            }
        ),
        content_type="application/json",
    )

    assert created.status_code == 201
    assert len(mail.outbox) == 1
    uid, token = extract_setup_link_params(mail.outbox[0].body)

    invite_user = User.objects.get(email="totp-onboarding@example.com")
    assert invite_user.can_resend_setup_email is True

    password_response = activation_client.post(
        "/api/auth/password-reset/confirm/",
        data=json.dumps(
            {
                "uid": uid,
                "token": token,
                "new_password": "strong-password-456",
            }
        ),
        content_type="application/json",
    )

    assert password_response.status_code == 200
    assert password_response.json()["next_step"] == "totp_setup"

    invite_user.refresh_from_db()
    assert invite_user.email_setup_pending is True

    resend_while_totp_pending = client.post(
        f"/api/auth/users/{invite_user.id}/resend-setup-email/"
    )
    assert resend_while_totp_pending.status_code == 200
    assert resend_while_totp_pending.json()["can_resend_setup_email"] is True

    setup_response = activation_client.post(
        "/api/auth/2fa/setup/",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert setup_response.status_code == 200

    device = TOTPDevice.objects.get(user=invite_user, confirmed=False)
    confirm_response = activation_client.post(
        "/api/auth/2fa/confirm/",
        data=json.dumps({"token": build_totp_token(device)}),
        content_type="application/json",
    )

    assert confirm_response.status_code == 200

    invite_user.refresh_from_db()
    assert invite_user.email_setup_pending is False

    resend_after_totp = client.post(
        f"/api/auth/users/{invite_user.id}/resend-setup-email/"
    )
    assert resend_after_totp.status_code == 400
    assert resend_after_totp.json()["detail"] == "This user does not need a setup email."
