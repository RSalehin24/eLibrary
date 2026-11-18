

@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="anymail.backends.brevo.EmailBackend",
    EMAIL_HOST="smtp.example.com",
    EMAIL_PORT=587,
    EMAIL_HOST_USER="kindle-sender@example.com",
    EMAIL_HOST_PASSWORD="fake-smtp-key",
    ACCOUNT_INVITE_FROM_EMAIL="kindle-sender@example.com",
)
def test_send_to_kindle_falls_back_to_smtp_when_primary_backend_is_brevo(tmp_path, client, monkeypatch):
    selected_backends = []
    closed_connections = []

    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def close(self):
            closed_connections.append(True)

    def fake_get_connection(*args, **kwargs):
        selected_backends.append(kwargs.get("backend"))
        return DummyConnection()

    sent_bodies = []

    def fake_send(self, fail_silently=False):
        sent_bodies.append(self.body)
        return 1

    monkeypatch.setattr("apps.access.views.assets.get_connection", fake_get_connection)
    monkeypatch.setattr("django.core.mail.message.EmailMessage.send", fake_send)

    user = User.objects.create_user(
        email="kindle-reader-brevo@example.com",
        password="strong-password-123",
        kindle_emails=["reader-one@kindle.com"],
    )
    book = Book.objects.create(title="Kindle Brevo Fallback", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "kindle-brevo-fallback.epub"
    epub_path.write_bytes(b"epub")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.SEND_KINDLE)
    client.force_login(user)

    response = client.post(f"/api/access/books/{book.slug}/send-to-kindle/")

    assert response.status_code == 200
    assert selected_backends == ["django.core.mail.backends.smtp.EmailBackend"]
    assert sent_bodies == [""]
    assert closed_connections == [True]


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="anymail.backends.brevo.EmailBackend",
    EMAIL_HOST="smtp-relay.brevo.com",
    EMAIL_PORT=587,
    EMAIL_HOST_USER="library@example.com",
    EMAIL_HOST_PASSWORD="smtp-key",
    EMAIL_USE_TLS=True,
    ACCOUNT_INVITE_FROM_EMAIL="kindle-sender@example.com",
)
def test_send_to_kindle_uses_configured_smtp_credentials_for_brevo_backend(
    tmp_path, client, monkeypatch
):
    selected_connection_kwargs = []
    closed_connections = []

    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def close(self):
            closed_connections.append(True)

    def fake_get_connection(*args, **kwargs):
        selected_connection_kwargs.append(kwargs)
        return DummyConnection()

    monkeypatch.setattr("apps.access.views.assets.get_connection", fake_get_connection)
    monkeypatch.setattr("django.core.mail.message.EmailMessage.send", lambda self, fail_silently=False: 1)

    user = User.objects.create_user(
        email="kindle-reader-brevo-smtp-defaults@example.com",
        password="strong-password-123",
        kindle_emails=["reader-one@kindle.com"],
    )
    book = Book.objects.create(title="Kindle Brevo SMTP Defaults", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "kindle-brevo-smtp-defaults.epub"
    epub_path.write_bytes(b"epub")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.SEND_KINDLE)
    client.force_login(user)

    response = client.post(f"/api/access/books/{book.slug}/send-to-kindle/")

    assert response.status_code == 200
    assert len(selected_connection_kwargs) == 1
    connection_kwargs = selected_connection_kwargs[0]
    assert connection_kwargs["backend"] == "django.core.mail.backends.smtp.EmailBackend"
    assert connection_kwargs["host"] == "smtp-relay.brevo.com"
    assert connection_kwargs["port"] == 587
    assert connection_kwargs["username"] == "library@example.com"
    assert connection_kwargs["password"] == "smtp-key"
    assert connection_kwargs["use_tls"] is True
    assert closed_connections == [True]


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="anymail.backends.brevo.EmailBackend",
    EMAIL_HOST="",
    EMAIL_PORT=587,
    EMAIL_HOST_USER="library@example.com",
    EMAIL_HOST_PASSWORD="",
    EMAIL_USE_TLS=True,
    ACCOUNT_INVITE_FROM_EMAIL="kindle-sender@example.com",
)
def test_send_to_kindle_returns_502_when_smtp_config_is_missing(tmp_path, client):
    user = User.objects.create_user(
        email="kindle-reader-missing-smtp@example.com",
        password="strong-password-123",
        kindle_emails=["reader-one@kindle.com"],
    )
    book = Book.objects.create(title="Kindle Missing SMTP Host", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "kindle-missing-smtp.epub"
    epub_path.write_bytes(b"epub")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.SEND_KINDLE)
    client.force_login(user)

    response = client.post(f"/api/access/books/{book.slug}/send-to-kindle/")

    assert response.status_code == 502
    payload = response.json()
    assert "Kindle delivery requires SMTP" in payload["detail"]
    assert payload["failedEmails"] == ["reader-one@kindle.com"]
    assert payload["senderEmail"] == "kindle-sender@example.com"


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="anymail.backends.brevo.EmailBackend",
    EMAIL_HOST="smtp-relay.brevo.com",
    EMAIL_PORT=587,
    EMAIL_HOST_USER="library@example.com",
    EMAIL_HOST_PASSWORD="wrong-smtp-password",
    EMAIL_USE_TLS=True,
    ACCOUNT_INVITE_FROM_EMAIL="kindle-sender@example.com",
)
def test_send_to_kindle_returns_specific_502_when_smtp_authentication_fails(
    tmp_path, client, monkeypatch
):
    selected_connection_kwargs = []
    closed_connections = []

    class DummyConnection:
        def __init__(self, kwargs):
            self.kwargs = kwargs

        def close(self):
            closed_connections.append(
                (self.kwargs.get("username"), self.kwargs.get("password"))
            )

    def fake_get_connection(*args, **kwargs):
        selected_connection_kwargs.append(kwargs)
        return DummyConnection(kwargs)

    def fake_send(self, fail_silently=False):
        raise SMTPAuthenticationError(535, b"5.7.8 Authentication failed")

    monkeypatch.setattr("apps.access.views.assets.get_connection", fake_get_connection)
    monkeypatch.setattr("django.core.mail.message.EmailMessage.send", fake_send)

    user = User.objects.create_user(
        email="kindle-reader-brevo-auth-fail@example.com",
        password="strong-password-123",
        kindle_emails=["reader-one@kindle.com"],
    )
    book = Book.objects.create(
        title="Kindle Brevo SMTP Auth Failure",
        state="ready",
        review_state="approved",
    )
    epub_path = Path(tmp_path) / "kindle-brevo-auth-failure.epub"
    epub_path.write_bytes(b"epub")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.SEND_KINDLE)
    client.force_login(user)

    response = client.post(f"/api/access/books/{book.slug}/send-to-kindle/")

    assert response.status_code == 502
    payload = response.json()
    assert "could not authenticate with Brevo SMTP" in payload["detail"]
    assert "API key will not work for SMTP" in payload["detail"]
    assert payload["failedEmails"] == ["reader-one@kindle.com"]
    assert len(selected_connection_kwargs) == 1
    assert selected_connection_kwargs[0]["username"] == "library@example.com"
    assert selected_connection_kwargs[0]["password"] == "wrong-smtp-password"
    assert closed_connections == [("library@example.com", "wrong-smtp-password")]
