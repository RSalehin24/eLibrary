import json

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    Contributor,
    MetadataVersion,
)


@pytest.mark.django_db
def test_staff_can_confirm_duplicate_review_to_existing_book(client):
    actor = User.objects.create_superuser(
        email="removed-review@example.test", password="strong-password-123"
    )
    book = Book.objects.create(title="অপরিবর্তিত বই")
    client.force_login(actor)
    response = client.post(
        f"/api/ingestion/duplicate-reviews/{book.pk}/resolve/",
        data=json.dumps({"decision": "confirm_existing"}),
        content_type="application/json",
    )
    assert response.status_code == 404
    book.refresh_from_db()
    assert book.state == "draft" and not MetadataVersion.objects.exists()


@pytest.mark.django_db
def test_metadata_edit_scope_allows_non_staff_editor(client):
    actor = User.objects.create_user(
        email="editor@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="অপরিবর্তিত বই")
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    client.force_login(actor)
    response = client.patch(
        f"/api/catalog/books/{book.slug}/metadata/",
        data=json.dumps(
            {"summary": "forbidden", "expected_updated_at": book.updated_at.isoformat()}
        ),
        content_type="application/json",
    )
    assert response.status_code == 404
    book.refresh_from_db()
    assert book.summary == "" and not MetadataVersion.objects.exists()


@pytest.mark.django_db
def test_metadata_update_drops_author_role_when_same_name_is_translator_or_editor(
    client,
):
    actor = User.objects.create_superuser(
        email="roles@example.test", password="strong-password-123"
    )
    book = Book.objects.create(title="দুই ভূমিকার বই")
    contributor = Contributor.objects.create(name="একই সহযোগী")
    client.force_login(actor)
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/relationships/",
        data=json.dumps(
            {
                "expected_updated_at": book.updated_at.isoformat(),
                "contributors": [
                    {"id": str(contributor.pk), "role": role}
                    for role in ["author", "translator"]
                ],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert set(book.book_contributors.values_list("role", flat=True)) == {
        "author",
        "translator",
    }


@pytest.mark.django_db
def test_metadata_edit_scope_allows_non_staff_editor_to_soft_delete_book(client):
    actor = User.objects.create_user(
        email="delete-editor@example.test", password="strong-password-123"
    )
    book = Book.objects.create(title="অপরিবর্তিত বই")
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    client.force_login(actor)
    assert client.delete(f"/api/catalog/books/{book.slug}/").status_code == 403
    book.refresh_from_db()
    assert book.deleted_at is None and book.state == "draft"


@pytest.mark.django_db
def test_book_delete_requires_metadata_edit_scope(client):
    user = User.objects.create_user(
        email="reader-delete@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="নিরাপদ বই", state="ready")
    client.force_login(user)

    response = client.delete(f"/api/catalog/books/{book.slug}/")

    assert response.status_code == 403
    book.refresh_from_db()
    assert book.deleted_at is None


@pytest.mark.django_db
def test_processing_manage_scope_allows_non_staff_duplicate_resolution(client):
    actor = User.objects.create_superuser(
        email="removed-review@example.test", password="strong-password-123"
    )
    book = Book.objects.create(title="অপরিবর্তিত বই")
    client.force_login(actor)
    response = client.post(
        f"/api/ingestion/duplicate-reviews/{book.pk}/resolve/",
        data=json.dumps({"decision": "confirm_existing"}),
        content_type="application/json",
    )
    assert response.status_code == 404
    book.refresh_from_db()
    assert book.state == "draft" and not MetadataVersion.objects.exists()


@pytest.mark.django_db
def test_metadata_review_endpoints_update_book_review_state(client):
    actor = User.objects.create_superuser(
        email="removed-metadata-review@example.test", password="strong-password-123"
    )
    book = Book.objects.create(title="অপ্রকাশিত বই")
    client.force_login(actor)
    path = f"/api/catalog/books/{book.slug}/metadata-reviews/"
    assert client.get(path).status_code == 404
    assert (
        client.post(
            path,
            data=json.dumps({"state": "approved"}),
            content_type="application/json",
        ).status_code
        == 404
    )
    book.refresh_from_db()
    assert book.state == "draft" and not hasattr(book, "review_state")
