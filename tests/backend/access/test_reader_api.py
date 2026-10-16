from datetime import timedelta

import pytest
from apps.access.models import (
    BookOpeningRecord,
    PermissionGrant,
    PermissionScope,
    PreviewAccessSession,
    ReadingSession,
)
from apps.accounts.models import User
from apps.catalog.models import UserBook
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def launch(client, book):
    return client.post(f"/api/v1/reading/books/{book.slug}/launch/")


def test_session_is_account_bound_and_does_not_expose_bearer_tokens(reader):
    client, _, book, _, _ = reader
    response = launch(client, book)
    assert response.status_code == 200
    data = response.json()
    assert data["chapters"][0]["label"] == "প্রথম অধ্যায়"
    assert data["resource_base"].endswith("/resources/")
    assert "token" not in data and "storage_reference" not in data
    path = f"/api/v1/reading/sessions/{data['id']}/"
    assert client.get(path).status_code == 200
    client.force_authenticate(
        User.objects.create_user(email="other-reader@library.test")
    )
    assert client.get(path).status_code == 404
    assert APIClient().get(path).status_code == 403
    assert response["Cache-Control"] == "private, no-store"


def test_resources_are_protected_and_sandboxed(reader):
    client, _, book, _, _ = reader
    data = launch(client, book).json()
    path = data["resource_base"] + "OEBPS/chapter-1.xhtml"
    response = client.get(path)
    assert response.status_code == 200
    assert "বাংলা বইয়ের প্রথম পাতা" in b"".join(response.streaming_content).decode()
    assert "sandbox allow-same-origin" in response["Content-Security-Policy"]
    assert "default-src 'none'" in response["Content-Security-Policy"]
    assert data["resource_base"] in response["Content-Security-Policy"]
    assert "img-src 'self'" not in response["Content-Security-Policy"]
    assert response["X-Frame-Options"] == "SAMEORIGIN"
    assert response["Cache-Control"] == "private, no-store"
    assert APIClient().get(path).status_code == 403
    assert (
        client.get(data["resource_base"] + "META-INF/container.xml").status_code == 404
    )
    assert client.get(data["resource_base"] + "OEBPS/../package.opf").status_code == 404


def test_protected_storage_has_no_public_media_route(reader):
    _, _, _, _, publication = reader
    path = (
        f"/media/protected/reader/{publication.storage_reference}/OEBPS/chapter-1.xhtml"
    )
    assert Client().get(path).status_code == 404
    assert Client().get("/media/generated/book/book.epub").status_code == 404


def test_expired_session_and_deleted_book_are_unavailable(reader):
    client, _, book, _, _ = reader
    data = launch(client, book).json()
    path = f"/api/v1/reading/sessions/{data['id']}/"
    PreviewAccessSession.objects.filter(pk=data["id"]).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert client.get(path).status_code == 404
    book.deleted_at = timezone.now()
    book.save(update_fields=["deleted_at"])
    assert launch(client, book).status_code == 404


def test_revoked_grant_blocks_existing_session_and_resources(reader):
    client, user, book, _, _ = reader
    UserBook.objects.filter(user=user, book=book).delete()
    grant = PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_DURABLE
    )
    data = launch(client, book).json()
    grant.is_active = False
    grant.save()
    assert client.get(f"/api/v1/reading/sessions/{data['id']}/").status_code == 403
    assert (
        client.get(data["resource_base"] + "OEBPS/chapter-1.xhtml").status_code == 403
    )
    assert launch(client, book).status_code == 403


def test_read_once_allows_current_session_but_rejects_a_second_launch(reader):
    client, user, book, _, _ = reader
    UserBook.objects.filter(user=user, book=book).delete()
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    data = launch(client, book).json()
    assert launch(client, book).status_code == 403
    assert client.get(f"/api/v1/reading/sessions/{data['id']}/").status_code == 200
    assert (
        client.get(data["resource_base"] + "OEBPS/chapter-2.xhtml").status_code == 200
    )
    assert BookOpeningRecord.objects.filter(user=user, book=book).count() == 1


def test_unprepared_asset_does_not_consume_read_once(reader):
    client, user, book, asset, _ = reader
    UserBook.objects.filter(user=user, book=book).delete()
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    asset.checksum = ""
    asset.save(update_fields=["checksum"])
    response = launch(client, book)
    assert response.status_code == 409
    assert response.json()["code"] == "reader_not_ready"
    assert not BookOpeningRecord.objects.filter(user=user, book=book).exists()


def test_download_action_requires_an_available_ready_asset(reader):
    client, _, book, asset, _ = reader
    asset.status = "failed"
    asset.save(update_fields=["status"])
    access = client.get(f"/api/v1/reading/books/{book.slug}/access/").json()
    assert access["can_download"] is False


def test_resources_do_not_select_book_content_blobs(reader, django_assert_num_queries):
    client, _, book, _, _ = reader
    data = launch(client, book).json()
    with django_assert_num_queries(2) as queries:
        response = client.get(data["resource_base"] + "OEBPS/chapter-1.xhtml")
    assert response.status_code == 200
    assert all(
        '"main_content_html"' not in entry["sql"] for entry in queries.captured_queries
    )


def test_read_once_does_not_grant_download_permission(reader):
    client, user, book, _, _ = reader
    UserBook.objects.filter(user=user, book=book).delete()
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.READ_ONCE
    )
    access = client.get(f"/api/v1/reading/books/{book.slug}/access/").json()
    assert access["can_read"] is True and access["prepared"] is True
    assert access["can_download"] is False
    assert client.get(f"/api/v1/reading/books/{book.slug}/download/").status_code == 403
    data = launch(client, book).json()
    access = client.get(f"/api/v1/reading/books/{book.slug}/access/").json()
    assert access["can_read"] is False
    assert access["active_session_id"] == data["id"]


def test_session_launch_and_progress_require_csrf(reader):
    _, user, book, _, _ = reader
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    path = f"/api/v1/reading/books/{book.slug}/launch/"
    assert client.post(path).status_code == 403
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    data = client.post(path, HTTP_X_CSRFTOKEN=token).json()
    progress_path = f"/api/v1/reading/sessions/{data['id']}/progress/"
    fields = {"last_location": "chapter:0:0", "progress_percent": 0}
    assert (
        client.put(progress_path, fields, content_type="application/json").status_code
        == 403
    )
    assert (
        client.put(
            progress_path,
            fields,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )


def test_progress_is_private_and_persisted(reader):
    client, user, book, _, _ = reader
    data = launch(client, book).json()
    path = f"/api/v1/reading/sessions/{data['id']}/progress/"
    response = client.put(
        path, {"last_location": "chapter:1:0.4", "progress_percent": 70}, format="json"
    )
    assert response.status_code == 200
    state = ReadingSession.objects.get(user=user, book=book)
    assert state.progress_percent == 70
    assert state.last_location == "chapter:1:0.4"
    client.force_authenticate(
        User.objects.create_user(email="stranger-progress@library.test")
    )
    assert (
        client.put(
            path, {"last_location": "", "progress_percent": 0}, format="json"
        ).status_code
        == 404
    )


@pytest.mark.parametrize("progress", [-1, 101, "NaN", "Infinity"])
def test_progress_rejects_out_of_range_and_nonfinite_values(reader, progress):
    client, _, book, _, _ = reader
    data = launch(client, book).json()
    response = client.put(
        f"/api/v1/reading/sessions/{data['id']}/progress/",
        {"last_location": "", "progress_percent": progress},
        format="json",
    )
    assert response.status_code == 400
    assert "progress_percent" in response.json()["field_errors"]
