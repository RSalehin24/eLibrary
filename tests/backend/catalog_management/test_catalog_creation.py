from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, MetadataVersion, UserBook
from apps.common.models import AuditLog
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
URL = "/api/v1/manage/books/"


@pytest.fixture
def catalog_creator():
    user = User.objects.create_user(email="catalog-creator@library.test", is_staff=True)
    client = APIClient()
    client.force_authenticate(user)
    return user, client


def creation_values():
    return {
        "operation_id": str(uuid4()),
        "title": "নতুন বইয়ের নথি",
        "edition": "দ্বিতীয় সংস্করণ",
        "language": "bn",
        "publisher": "পরীক্ষার প্রকাশক",
        "is_compilation": True,
    }


def test_creation_starts_unpublished_and_never_creates_ownership(catalog_creator):
    user, client = catalog_creator
    values = creation_values()
    response = client.post(URL, values, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == values["operation_id"]
    assert data["state"] == "draft"
    assert "review_state" not in data and "record_type" not in data
    assert "editorial_reviewed_at" not in data and (not data["indexing_eligible"])
    for field in (
        "edition",
        "language",
        "publisher",
        "is_compilation",
    ):
        assert data[field] == values[field]
    assert not UserBook.objects.exists()
    audit = AuditLog.objects.get(pk=values["operation_id"])
    assert audit.actor == user and audit.payload["publisher"] == "পরীক্ষার প্রকাশক"
    assert client.get(f"/api/v1/catalog/books/{data['slug']}/").status_code == 404


def test_creation_replay_returns_current_record_but_rejects_changed_input(
    catalog_creator,
):
    _, client = catalog_creator
    values = creation_values()
    first = client.post(URL, values, format="json").json()
    assert client.post(URL, values, format="json").json() == first
    book = Book.objects.get(pk=first["id"])
    book.title = "সম্পাদিত বইয়ের নথি"
    book.save()
    replayed = client.post(URL, values, format="json")
    assert replayed.status_code == 201 and replayed.json()["slug"] == book.slug
    conflict = client.post(URL, {**values, "edition": "প্রথম সংস্করণ"}, format="json")
    assert conflict.status_code == 409 and Book.objects.count() == 1
    assert AuditLog.objects.count() == 1


def test_creation_status_is_private_to_its_creator(catalog_creator):
    _, client = catalog_creator
    values = creation_values()
    client.post(URL, values, format="json")
    path = f"/api/v1/manage/book-creations/{values['operation_id']}/"
    response = client.get(path)
    assert (
        response.status_code == 200 and response["Cache-Control"] == "private, no-store"
    )
    other = User.objects.create_user(email="other-creator@library.test", is_staff=True)
    client.force_authenticate(other)
    assert client.get(path).status_code == 404
    assert client.post(URL, values, format="json").status_code == 409
    assert APIClient().get(path).status_code == 403


@pytest.mark.parametrize(
    "scope", [None, PermissionScope.METADATA_EDIT, PermissionScope.PROCESSING_MANAGE]
)
def test_creation_requires_global_metadata_authority(scope):
    user = User.objects.create_user(email="scoped-creator@library.test")
    if scope:
        book = Book.objects.create(title="সীমিত সম্পাদনা")
        PermissionGrant.objects.create(user=user, scope=scope, book=book)
    client = APIClient()
    client.force_authenticate(user)
    assert not client.get("/api/v1/auth/session/").json()["workspaces"][
        "can_create_books"
    ]
    assert client.post(URL, creation_values(), format="json").status_code == 403
    assert not AuditLog.objects.exists() and not UserBook.objects.exists()


@pytest.mark.parametrize(
    "values,field",
    [
        ({"title": "!!!"}, "title"),
        ({"manual_price": "-1.00"}, "manual_price"),
        ({"language": "not a language"}, "language"),
        ({"manual_binding": "unknown"}, "manual_binding"),
        ({"record_type": "unknown"}, "record_type"),
        ({"state": "published"}, "state"),
        ({"edition": "a" * 121}, "edition"),
    ],
)
def test_invalid_creation_is_atomic_and_reports_fields(catalog_creator, values, field):
    _, client = catalog_creator
    response = client.post(URL, {**creation_values(), **values}, format="json")
    assert response.status_code == 400 and field in response.json()["field_errors"]
    assert not Book.objects.exists() and not AuditLog.objects.exists()


def test_bibliographic_edits_keep_revision_control_and_original_values(
    catalog_creator,
):
    _, client = catalog_creator
    created = client.post(URL, creation_values(), format="json").json()
    path = URL + created["slug"] + "/"
    values = {
        "expected_updated_at": created["updated_at"],
        "edition": "তৃতীয় সংস্করণ",
        "publisher": "সংশোধিত প্রকাশক",
    }
    response = client.patch(path, values, format="json")
    assert (
        response.status_code == 200 and response.json()["publisher"] == "সংশোধিত প্রকাশক"
    )
    snapshot = MetadataVersion.objects.get().snapshot
    assert (
        snapshot["publisher"] == "পরীক্ষার প্রকাশক"
        and snapshot["edition"] == "দ্বিতীয় সংস্করণ"
    )
    assert client.patch(path, values, format="json").status_code == 409
    assert MetadataVersion.objects.count() == 1


def test_session_creation_requires_csrf(catalog_creator):
    user, _ = catalog_creator
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post(URL, creation_values(), format="json").status_code == 403
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    response = client.post(
        URL, creation_values(), format="json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 201
