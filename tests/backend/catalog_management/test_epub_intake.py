from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.editorial.epub_uploads import prepare_uploaded_assets
from apps.catalog.models import Book, GeneratedAsset
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from ..access.reader_fixtures import write_epub

pytestmark = pytest.mark.django_db


@pytest.fixture
def intake(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    actor = User.objects.create_user(email="intake@library.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.METADATA_EDIT)
    client = APIClient()
    client.force_authenticate(actor)
    response = client.post(
        "/api/v1/manage/books/",
        {
            "operation_id": str(uuid4()),
            "title": "নিজের যোগ করা বই",
        },
        format="json",
    )
    assert response.status_code == 201
    book = Book.objects.get(pk=response.json()["id"])
    return actor, book, client, write_epub(tmp_path / "book.epub")


def upload_intake(fixture):
    _, book, client, path = fixture
    return client.post(
        f"/api/v1/manage/book-creations/{book.pk}/epub/",
        {
            "expected_updated_at": book.updated_at.isoformat(),
            "file": SimpleUploadedFile("book.epub", path.read_bytes()),
        },
        format="multipart",
    )


def test_creator_can_complete_initial_intake_and_replay_without_existing_book_edit_rights(
    intake,
):
    _, book, client, _ = intake
    assert client.get(f"/api/v1/manage/books/{book.slug}/").status_code == 404
    response = upload_intake(intake)
    assert response.status_code == 200 and response.json()["state"] == "published"
    revision = response.json()["updated_at"]
    assert upload_intake(intake).json()["updated_at"] == revision
    assert set(GeneratedAsset.objects.values_list("asset_type", flat=True)) == {
        "epub",
        "html",
    }
    assert (
        client.get(f"/api/v1/reading/books/{book.slug}/access/").json()["can_edit_book"]
        is False
    )
    assert Book.objects.count() == 1


def test_completed_intake_cannot_be_used_to_replace_an_existing_book(intake):
    assert upload_intake(intake).status_code == 200
    revision = Book.objects.get(pk=intake[1].pk).updated_at
    write_epub(
        intake[3], {"OEBPS/chapter-2.xhtml": "<html><body>Changed</body></html>"}
    )
    assert upload_intake(intake).status_code == 409
    assert Book.objects.get(pk=intake[1].pk).updated_at == revision


def test_intake_rechecks_revoked_creation_authority_before_activation(
    intake, monkeypatch
):
    actor, book, _, _ = intake

    def revoked_during_preparation(candidate, upload):
        staged = prepare_uploaded_assets(candidate, upload)
        PermissionGrant.objects.filter(user=actor).update(is_active=False)
        return staged

    monkeypatch.setattr(
        "apps.catalog.editorial.epub_intake.prepare_uploaded_assets",
        revoked_during_preparation,
    )
    assert upload_intake(intake).status_code == 403
    book.refresh_from_db()
    assert book.state == "draft" and not GeneratedAsset.objects.exists()


def test_intake_does_not_accept_another_creators_identifier(intake):
    _, book, client, _ = intake
    other = User.objects.create_user(email="other-intake@library.test", is_staff=True)
    client.force_authenticate(other)
    assert upload_intake(intake).status_code == 404
    book.refresh_from_db()
    assert book.state == "draft" and not GeneratedAsset.objects.exists()
