

@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://127.0.0.1:5173",
    FRONTEND_PORT="5173",
    PASSWORD_RESET_TIMEOUT=6 * 60 * 60,
)
def test_password_reset_request_sends_reset_confirm_link_email(client):
    user = User.objects.create_user(
        email="reset-request@example.com",
        password="strong-password-123",
        full_name="Reset Request",
    )

    response = client.post(
        "/api/auth/password-reset/",
        data=json.dumps({"email": user.email}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "Reset email has been sent."
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert (
        "http://127.0.0.1:5173/reset-password/confirm?uid=" in mail.outbox[0].body
    )
    assert (
        "This link stays valid for 6 hours from the time it was generated."
        in mail.outbox[0].body
    )
    assert "&amp;" not in mail.outbox[0].body

    html_body, html_mimetype = mail.outbox[0].alternatives[0]
    assert html_mimetype == "text/html"
    assert "Reset your password" in html_body
    assert "Reset Password" in html_body
    assert "This link stays valid for" in html_body
    assert "6 hours" in html_body
    assert "display: block;" in html_body
    assert "Reset password link:" in html_body
    assert "This is an automated message from 127.0.0.1:5173." in html_body


@pytest.mark.django_db
@override_settings(PASSWORD_RESET_TIMEOUT=6 * 60 * 60)
def test_password_reset_links_expire_after_six_hours(client):
    user = User.objects.create_user(
        email="reset-expiry@example.com",
        password="strong-password-123",
        full_name="Reset Expiry",
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    generator = password_link_token_generator
    issued_at = datetime.now()

    with patch.object(PasswordLinkTokenGenerator, "_now", return_value=issued_at):
        token = generator.make_token(user)

    request_body = json.dumps({"uid": uid, "token": token})

    with patch.object(
        PasswordLinkTokenGenerator,
        "_now",
        return_value=issued_at + timedelta(hours=5, minutes=59),
    ):
        valid_response = client.post(
            "/api/auth/password-reset/validate/",
            data=request_body,
            content_type="application/json",
        )

    assert valid_response.status_code == 200
    assert valid_response.json()["detail"] == "Password link is valid."

    with patch.object(
        PasswordLinkTokenGenerator,
        "_now",
        return_value=issued_at + timedelta(hours=6, minutes=1),
    ):
        expired_response = client.post(
            "/api/auth/password-reset/validate/",
            data=request_body,
            content_type="application/json",
        )

    assert expired_response.status_code == 400
    assert expired_response.json()["detail"] == "Reset token is invalid or expired."


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://127.0.0.1:5173",
    FRONTEND_PORT="5173",
)
def test_latest_password_reset_request_invalidates_any_previous_reset_links(client):
    user = User.objects.create_user(
        email="repeat-reset@example.com",
        password="strong-password-123",
        full_name="Repeat Reset",
    )
    password_client = APIClient()

    first_response = client.post(
        "/api/auth/password-reset/",
        data=json.dumps({"email": user.email}),
        content_type="application/json",
    )
    second_response = client.post(
        "/api/auth/password-reset/",
        data=json.dumps({"email": user.email}),
        content_type="application/json",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(mail.outbox) == 2

    first_uid, first_token = extract_reset_link_params(mail.outbox[0].body)
    second_uid, second_token = extract_reset_link_params(mail.outbox[1].body)

    assert first_uid == second_uid
    assert first_token != second_token

    first_validate = password_client.post(
        "/api/auth/password-reset/validate/",
        data=json.dumps({"uid": first_uid, "token": first_token}),
        content_type="application/json",
    )
    second_validate = password_client.post(
        "/api/auth/password-reset/validate/",
        data=json.dumps({"uid": second_uid, "token": second_token}),
        content_type="application/json",
    )

    assert first_validate.status_code == 400
    assert first_validate.json()["detail"] == "Reset token is invalid or expired."
    assert second_validate.status_code == 200
    assert second_validate.json()["detail"] == "Password link is valid."

    first_confirm = password_client.post(
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
    second_confirm = password_client.post(
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

    assert first_confirm.status_code == 400
    assert first_confirm.json()["detail"] == "Reset token is invalid or expired."
    assert second_confirm.status_code == 200
    assert second_confirm.json()["next_step"] == "login"

    user.refresh_from_db()
    assert user.check_password("strong-password-456") is True


@pytest.mark.django_db
def test_password_reset_confirm_returns_clean_short_password_error(client):
    user = User.objects.create_user(
        email="short-password@example.com",
        password="strong-password-123",
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)

    response = client.post(
        "/api/auth/password-reset/confirm/",
        data=json.dumps(
            {
                "uid": uid,
                "token": token,
                "new_password": "short",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Ensure this field has at least 12 characters."


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://127.0.0.1:5173",
    FRONTEND_PORT="5173",
)
def test_password_reset_request_omits_invited_users_with_pending_setup(client):
    invited_user = User.objects.create_user(
        email="pending-setup@example.com",
        password=None,
        full_name="Pending Setup",
        email_setup_pending=True,
    )

    response = client.post(
        "/api/auth/password-reset/",
        data=json.dumps({"email": invited_user.email}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No user exist with this email."
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_request_returns_missing_user_message_when_email_is_unknown(client):
    response = client.post(
        "/api/auth/password-reset/",
        data=json.dumps({"email": "missing-user@example.com"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No user exist with this email."
    assert len(mail.outbox) == 0
