

@pytest.mark.django_db
def test_send_to_kindle_ignores_invalid_legacy_domains(tmp_path, client):
    user = User.objects.create_user(
        email="kindle-reader-legacy@example.com",
        password="strong-password-123",
        kindle_emails=["reader-one@kindle.com", "reader-two@example.com"],
    )
    book = Book.objects.create(title="Kindle Delivery Legacy", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "kindle-delivery-legacy.epub"
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
    payload = response.json()
    assert payload["deliveredEmails"] == ["reader-one@kindle.com"]
    assert payload["failedEmails"] == []
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["reader-one@kindle.com"]


@pytest.mark.django_db
def test_send_to_kindle_requires_configured_emails(tmp_path, client):
    user = User.objects.create_user(
        email="missing-kindle@example.com",
        password="strong-password-123",
    )
    book = Book.objects.create(title="Missing Kindle Config", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "missing-kindle.epub"
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

    assert response.status_code == 400
    assert response.json()["detail"] == "Add at least one Kindle email in your profile before sending."


@pytest.mark.django_db
def test_html_download_inlines_stale_relative_cover_references(tmp_path, client):
    user = User.objects.create_user(email="html-download@example.com", password="strong-password-123")
    book = Book.objects.create(title="HTML Download Book", state="ready", review_state="approved")
    html_path = Path(tmp_path) / "book.html"
    cover_path = Path(tmp_path) / "book_cover.jpg"
    html_path.write_text(
        "<!DOCTYPE html><html><body><img src='book_image.hpg' alt='Book Cover' class='cover-image'></body></html>",
        encoding="utf-8",
    )
    cover_path.write_bytes(b"cover-bytes")

    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.COVER,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(cover_path),
        content_type="image/jpeg",
        file_size=cover_path.stat().st_size,
    )

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.PREVIEW_HTML)
    client.force_login(user)

    response = client.get(f"/api/access/books/{book.slug}/download/html/")

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "data:image/jpeg;base64," in body
    assert "book_image.hpg" not in body
