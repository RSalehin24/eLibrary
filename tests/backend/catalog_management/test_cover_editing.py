from io import BytesIO
from unittest.mock import patch

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset
from apps.common.models import AuditLog
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def image_upload():
    content = BytesIO()
    Image.new("RGB", (30, 40), "green").save(content, "JPEG")
    return SimpleUploadedFile("cover.jpg", content.getvalue(), "image/jpeg")


@pytest.fixture
def cover_editor():
    actor = User.objects.create_user(email="cover-editor@example.test", is_staff=True)
    book = Book.objects.create(title="Cover editing", state="published")
    client = APIClient()
    client.force_authenticate(actor)
    return client, book, actor


def cover_url(book):
    return f"/api/v1/manage/books/{book.slug}/cover/"


def upload_cover(fixture):
    client, book, _ = fixture
    return client.post(
        cover_url(book),
        {"expected_updated_at": book.updated_at.isoformat(), "image": image_upload()},
        format="multipart",
    )


def test_cover_upload_normalizes_bytes_preserves_publication_and_can_be_removed(
    cover_editor,
):
    client, book, _ = cover_editor
    response = upload_cover(cover_editor)
    assert response.status_code == 200
    assert response.data["state"] == "published"
    assert response.data["file_metadata_may_differ"]
    asset = GeneratedAsset.objects.get(book=book, asset_type="cover")
    assert asset.content_type == "image/png"
    with asset.file.open("rb") as content, Image.open(content) as image:
        assert image.format == "PNG" and image.size == (30, 40)
    book.refresh_from_db()
    assert book.metadata_overrides["cover"] == asset.checksum
    removed = client.delete(
        cover_url(book),
        {"expected_updated_at": book.updated_at.isoformat()},
        format="json",
    )
    assert removed.status_code == 200 and removed.data["cover_url"] is None
    book.refresh_from_db()
    assert book.state == "published" and book.metadata_overrides["cover"] is None
    assert not GeneratedAsset.objects.filter(book=book, asset_type="cover").exists()
    assert AuditLog.objects.filter(verb="catalog.cover.update").count() == 2


@pytest.mark.parametrize("administrator", [False, True])
def test_cover_edit_requires_current_administrator_authority(
    cover_editor, administrator
):
    _, book, actor = cover_editor
    actor.is_staff = administrator
    actor.save()
    response = upload_cover(cover_editor)
    assert response.status_code == (200 if administrator else 404)
    assert GeneratedAsset.objects.filter(book=book).exists() == administrator


def test_invalid_cover_and_stale_command_keep_the_previous_cover(cover_editor):
    client, book, _ = cover_editor
    assert upload_cover(cover_editor).status_code == 200
    asset = GeneratedAsset.objects.get(book=book, asset_type="cover")
    checksum, filename = asset.checksum, asset.file.name
    assert upload_cover(cover_editor).status_code == 409
    book.refresh_from_db()
    response = client.post(
        cover_url(book),
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "image": SimpleUploadedFile("fake.png", b"not an image", "image/png"),
        },
        format="multipart",
    )
    assert response.status_code == 400 and response.data["field_errors"]["image"]
    asset.refresh_from_db()
    assert (asset.checksum, asset.file.name) == (checksum, filename)


@pytest.mark.parametrize("failure", ["storage", "persistence"])
def test_failed_cover_commit_preserves_files_metadata_and_revision(
    cover_editor, failure
):
    _, book, _ = cover_editor
    assert upload_cover(cover_editor).status_code == 200
    book.refresh_from_db()
    revision, overrides = book.updated_at, dict(book.metadata_overrides)
    asset = GeneratedAsset.objects.get(book=book, asset_type="cover")
    checksum, filename = asset.checksum, asset.file.name
    if failure == "storage":
        with patch.object(
            asset.file.storage, "save", side_effect=OSError("storage unavailable")
        ):
            response = upload_cover(cover_editor)
    else:
        with patch(
            "apps.catalog.editorial.covers.AuditLog.objects.create",
            side_effect=OSError("persistence unavailable"),
        ):
            response = upload_cover(cover_editor)
    assert (
        response.status_code == 503 and response.data["code"] == "storage_unavailable"
    )
    book.refresh_from_db()
    asset.refresh_from_db()
    assert (book.updated_at, book.metadata_overrides) == (revision, overrides)
    assert (asset.checksum, asset.file.name) == (checksum, filename)
    assert AuditLog.objects.filter(verb="catalog.cover.update").count() == 1


def test_revocation_between_cover_staging_and_commit_blocks_activation(
    cover_editor, monkeypatch
):
    from apps.catalog.editorial.covers import stage_cover

    _, book, actor = cover_editor

    def stage_then_revoke(current, content):
        staged = stage_cover(current, content)
        User.objects.filter(pk=actor.pk).update(is_staff=False)
        return staged

    monkeypatch.setattr("apps.catalog.editorial.covers.stage_cover", stage_then_revoke)
    assert upload_cover(cover_editor).status_code == 404
    book.refresh_from_db()
    assert not book.generated_assets.exists() and book.metadata_overrides == {}
