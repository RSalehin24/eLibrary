from datetime import timedelta

import pytest
from apps.access.models import (
    Bookmark,
    Highlight,
    PermissionGrant,
    PermissionScope,
    PreviewAccessSession,
    ReadingSession,
)
from apps.access.publication_models import PreparationState, PreparedPublication
from apps.accounts.models import User
from apps.catalog.models import UserBook
from django.test import Client
from django.utils import timezone

pytestmark = pytest.mark.django_db


def create_annotation(reader, model):
    _, user, book, _, publication = reader
    values = {"location": "chapter:1:0.25"} if model is Bookmark else {
        "cfi_range": '{"start":0,"end":4}', "text": "বাংলা"
    }
    return model.objects.create(
        user=user, book=book, prepared_publication=publication,
        chapter_href="OEBPS/chapter-2.xhtml", **values,
    )


def annotation_path(annotation):
    kind = "bookmarks" if isinstance(annotation, Bookmark) else "highlights"
    return f"/api/v1/me/{kind}/{annotation.pk}/launch/"


@pytest.mark.parametrize("model", [Bookmark, Highlight])
def test_annotation_launch_keeps_original_edition_and_progress(reader, model):
    client, user, book, asset, publication = reader
    annotation = create_annotation(reader, model)
    original = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    client.put(f"/api/v1/reading/sessions/{original['id']}/progress/", {
        "last_location": "chapter:0:0.7500", "progress_percent": 37.5
    }, format="json")
    newer = PreparedPublication.objects.create(
        checksum="f" * 64, state=PreparationState.READY,
        manifest=publication.manifest, storage_reference=publication.storage_reference,
    )
    asset.checksum = newer.checksum
    asset.save(update_fields=["checksum"])
    current = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    response = client.post(annotation_path(annotation))
    assert response.status_code == 200
    session = PreviewAccessSession.objects.get(pk=response.json()["id"])
    assert session.prepared_publication == publication
    assert str(session.pk) != current["id"]
    state = ReadingSession.objects.get(user=user, book=book)
    assert state.last_location == "chapter:0:0.7500"
    assert str(state.preview_session_id) == original["id"]
    kind = "bookmarks" if model is Bookmark else "highlights"
    path = f"/api/v1/reading/sessions/{session.pk}/{kind}/{annotation.pk}/"
    assert client.get(path).json()["id"] == str(annotation.pk)
    wrong = path.replace(str(session.pk), current["id"])
    assert client.get(wrong).status_code == 404


@pytest.mark.parametrize("model", [Bookmark, Highlight])
def test_annotation_launch_checks_owner_and_current_permissions(reader, model):
    client, _, book, _, _ = reader
    annotation = create_annotation(reader, model)
    stranger = User.objects.create_user(email="other-note-owner@example.test")
    client.force_authenticate(stranger)
    assert client.post(annotation_path(annotation)).status_code == 404
    client.force_authenticate(reader[1])
    UserBook.objects.filter(book=book).delete()
    assert client.post(annotation_path(annotation)).status_code == 403
    assert not PreviewAccessSession.objects.exists()


@pytest.mark.parametrize("condition", ["failed", "missing", "obsolete"])
def test_annotation_launch_reports_unavailable_edition_without_losing_note(reader, condition):
    client, _, _, _, publication = reader
    annotation = create_annotation(reader, Bookmark)
    if condition == "failed":
        publication.state = PreparationState.FAILED
    elif condition == "missing":
        publication.storage_reference = "e" * 64
    else:
        publication.manifest = {**publication.manifest, "preparation_version": "obsolete"}
    publication.save()
    assert client.post(annotation_path(annotation)).status_code == 409
    annotation.refresh_from_db()
    assert annotation.prepared_publication == publication
    assert not PreviewAccessSession.objects.exists()


def test_legacy_annotation_launch_uses_current_publication(reader):
    annotation = create_annotation(reader, Bookmark)
    annotation.prepared_publication = None
    annotation.save()
    response = reader[0].post(annotation_path(annotation))
    assert response.status_code == 200
    session = PreviewAccessSession.objects.get(pk=response.json()["id"])
    assert session.prepared_publication == reader[4]


def test_annotation_launch_requires_csrf_and_keeps_response_private(reader):
    annotation = create_annotation(reader, Bookmark)
    client = Client(enforce_csrf_checks=True)
    client.force_login(reader[1])
    path = annotation_path(annotation)
    assert client.post(path).status_code == 403
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    response = client.post(path, HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]


def test_annotation_reuses_active_read_once_session_without_granting_another_opening(reader):
    client, user, book, _, _ = reader
    annotation = create_annotation(reader, Bookmark)
    UserBook.objects.filter(user=user, book=book).delete()
    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.READ_ONCE)
    opened = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    response = client.post(annotation_path(annotation))
    assert response.status_code == 200 and response.json()["id"] == opened["id"]
    assert PreviewAccessSession.objects.count() == 1
    PreviewAccessSession.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert client.post(annotation_path(annotation)).status_code == 403
    assert PreviewAccessSession.objects.count() == 1
