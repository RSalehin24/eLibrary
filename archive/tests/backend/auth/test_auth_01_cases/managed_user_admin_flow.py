

@pytest.mark.django_db
def test_superadmin_can_create_update_and_delete_managed_users_with_grants_and_totp_policy(client):
    superadmin = User.objects.create_superuser(
        email="superadmin@example.com",
        password="strong-password-123",
    )
    client.force_login(superadmin)

    created = client.post(
        "/api/auth/users/",
        data=json.dumps(
            {
                "email": "managed@example.com",
                "full_name": "Managed User",
                "password": "strong-password-456",
                "is_active": True,
                "totp_required": True,
                "global_scopes": ["read:durable", "download:file"],
            }
        ),
        content_type="application/json",
    )

    assert created.status_code == 201
    managed_user = User.objects.get(email="managed@example.com")
    assert managed_user.totp_required is True
    assert set(
        PermissionGrant.objects.active_for_user(managed_user)
        .filter(book__isnull=True)
        .values_list("scope", flat=True)
    ) == {"read:durable", "download:file"}

    updated = client.patch(
        f"/api/auth/users/{managed_user.id}/",
        data=json.dumps(
            {
                "full_name": "Updated Managed User",
                "totp_required": False,
                "global_scopes": ["metadata:edit"],
            }
        ),
        content_type="application/json",
    )

    assert updated.status_code == 200
    managed_user.refresh_from_db()
    assert managed_user.full_name == "Updated Managed User"
    assert managed_user.totp_required is False
    assert set(
        PermissionGrant.objects.active_for_user(managed_user)
        .filter(book__isnull=True)
        .values_list("scope", flat=True)
    ) == {"metadata:edit"}

    deleted = client.delete(f"/api/auth/users/{managed_user.id}/")
    assert deleted.status_code == 204
    assert not User.objects.filter(id=managed_user.id).exists()


@pytest.mark.django_db
def test_managed_users_list_returns_offset_pagination_payload(client):
    superadmin = User.objects.create_superuser(
        email="paged-superadmin@example.com",
        password="strong-password-123",
    )
    client.force_login(superadmin)

    for index in range(75):
        User.objects.create_user(
            email=f"managed-user-{index:02d}@example.com",
            password="strong-password-123",
            full_name=f"Managed User {index:02d}",
        )

    response = client.get("/api/auth/users/?offset=0&limit=60")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["rows"]) == 60
    assert payload["pagination"] == {
        "offset": 0,
        "limit": 60,
        "totalCount": 76,
        "hasMore": True,
        "nextOffset": 60,
    }


@pytest.mark.django_db
def test_managed_users_list_supports_search_filter_and_sort(client):
    superadmin = User.objects.create_superuser(
        email="filter-superadmin@example.com",
        password="strong-password-123",
    )
    User.objects.create_user(
        email="alpha@example.com",
        password="strong-password-123",
        full_name="Alpha User",
        is_active=True,
    )
    disabled_user = User.objects.create_user(
        email="bravo@example.com",
        password="strong-password-123",
        full_name="Bravo User",
        is_active=False,
    )
    scoped_user = User.objects.create_user(
        email="metadata@example.com",
        password="strong-password-123",
        full_name="Metadata User",
        is_active=True,
        totp_required=True,
    )
    PermissionGrant.objects.create(
        user=scoped_user,
        scope=PermissionScope.METADATA_EDIT,
        granted_by=superadmin,
    )
    client.force_login(superadmin)

    disabled_response = client.get(
        "/api/auth/users/?status=disabled&sort=email_desc"
    )
    assert disabled_response.status_code == 200
    assert [row["email"] for row in disabled_response.json()["rows"]] == [
        "bravo@example.com",
    ]

    permission_response = client.get(
        "/api/auth/users/?q=metadata&status=all&sort=email_asc"
    )
    assert permission_response.status_code == 200
    assert [row["email"] for row in permission_response.json()["rows"]] == [
        "metadata@example.com",
    ]

    required_response = client.get(
        "/api/auth/users/?q=required&status=all&sort=name_asc"
    )
    assert required_response.status_code == 200
    assert [row["email"] for row in required_response.json()["rows"]] == [
        "metadata@example.com",
    ]


@pytest.mark.django_db
def test_superadmin_cannot_edit_own_account_from_managed_users_endpoint(client):
    superadmin = User.objects.create_superuser(
        email="self-edit-block@example.com",
        password="strong-password-123",
    )
    client.force_login(superadmin)

    response = client.patch(
        f"/api/auth/users/{superadmin.id}/",
        data=json.dumps(
            {
                "full_name": "Attempted Self Edit",
                "global_scopes": ["read:durable"],
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot edit your own account from Users & Access."


@pytest.mark.django_db
def test_password_reset_confirm_requires_logout_when_authenticated(client):
    user = User.objects.create_user(
        email="reset-auth-block@example.com",
        password="strong-password-123",
    )
    client.force_login(user)

    response = client.post(
        "/api/auth/password-reset/confirm/",
        data=json.dumps(
            {
                "uid": "invalid",
                "token": "invalid",
                "new_password": "strong-password-456",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Please log out first before resetting a password from this link."


@pytest.mark.django_db
def test_password_reset_confirm_logs_in_users_who_must_finish_totp_setup(client):
    user = User.objects.create_user(
        email="totp-reset@example.com",
        password="strong-password-123",
        totp_required=True,
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)

    response = client.post(
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

    assert response.status_code == 200
    assert response.json()["next_step"] == "totp_setup"
    assert response.json()["user"]["totp_setup_required"] is True

    user.refresh_from_db()
    assert user.check_password("strong-password-456") is True

    session_response = client.get("/api/auth/session/")
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True
    assert session_response.json()["user"]["totp_setup_required"] is True


@pytest.mark.django_db
def test_password_reset_confirm_keeps_other_users_logged_out(client):
    user = User.objects.create_user(
        email="plain-reset@example.com",
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
                "new_password": "strong-password-456",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["next_step"] == "login"

    user.refresh_from_db()
    assert user.check_password("strong-password-456") is True

    session_response = client.get("/api/auth/session/")
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is False
