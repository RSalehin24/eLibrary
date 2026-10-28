import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, MetadataVersion
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def editor():
    user = User.objects.create_user(email="editor@library.test", is_staff=True)
    book = Book.objects.create(title="খসড়া বই", main_content_html="PRIVATE BODY")
    client = APIClient()
    client.force_authenticate(user)
    return client, book


def revision(book):
    book.refresh_from_db()
    return {"expected_updated_at": book.updated_at.isoformat()}


def command(client, book, action):
    return client.post(
        f"/api/v1/manage/books/{book.slug}/{action}/", revision(book), format="json"
    )


def test_admin_edit_preserves_publication_and_records_metadata_without_approval(editor):
    client, book = editor
    book.state = "published"
    book.save()
    previous_slug = book.slug
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/",
        {
            **revision(book),
            "title": "সংশোধিত বই",
            "editorial_description": "মূল পরিচিতি",
            "alternative_names": ["Book Alias"],
            "indexing_eligible": True,
        },
        format="json",
    )
    assert response.status_code == 200 and response.json()["state"] == "published"
    assert "review_state" not in response.json()
    assert "PRIVATE BODY" not in response.content.decode()
    book.refresh_from_db()
    assert book.slug != previous_slug
    assert MetadataVersion.objects.get(book=book).snapshot["title"] == "খসড়া বই"
    public = client.get(f"/api/v1/catalog/books/{previous_slug}/")
    assert public.status_code == 200 and public.json()["slug"] == book.slug
    assert public.json()["indexable"] is True
    assert command(client, book, "withdraw").status_code == 200
    assert client.get(f"/api/v1/catalog/books/{previous_slug}/").status_code == 404


@pytest.mark.parametrize(
    "scope", [PermissionScope.METADATA_EDIT, PermissionScope.ADMIN_FULL_CONTROL]
)
def test_scoped_editor_cannot_change_book_metadata(editor, scope):
    client, book = editor
    actor = User.objects.create_user(email="scoped@library.test")
    PermissionGrant.objects.create(user=actor, scope=scope, book=book)
    client.force_authenticate(actor)
    path = f"/api/v1/manage/books/{book.slug}/"
    assert client.get(path).status_code == 404
    assert (
        client.patch(
            path, {**revision(book), "summary": "forbidden"}, format="json"
        ).status_code
        == 404
    )
    assert not MetadataVersion.objects.exists()
    book.refresh_from_db()
    assert book.summary == ""


@pytest.mark.parametrize("action", ["review", "publish"])
def test_manual_approval_and_publication_endpoints_are_absent(editor, action):
    client, book = editor
    assert command(client, book, action).status_code == 404
    book.refresh_from_db()
    assert book.state == "draft"


def test_published_metadata_is_visible_without_a_manual_review(editor):
    client, book = editor
    book.state = "published"
    book.editorial_description = "DESCRIPTION"
    book.alternative_names = ["ALIAS"]
    book.seo_title = "TITLE"
    book.save()
    response = client.get(f"/api/v1/catalog/books/{book.slug}/")
    assert response.status_code == 200
    assert response.json()["editorial_description"] == book.editorial_description
    assert response.json()["seo_title"] == book.seo_title
    assert response.json()["indexable"] is False
    assert response.json()["alternative_names"] == book.alternative_names


def test_stale_updates_and_withdrawal_cannot_overwrite_a_newer_revision(editor):
    client, book = editor
    stale = revision(book)
    book.summary = "নতুন বর্ণনা"
    book.save()
    path = f"/api/v1/manage/books/{book.slug}/"
    response = client.patch(path, {**stale, "summary": "পুরোনো বর্ণনা"}, format="json")
    assert response.status_code == 409 and response.json()["code"] == "state_conflict"
    assert client.post(f"{path}withdraw/", stale, format="json").status_code == 409
    book.refresh_from_db()
    assert book.summary == "নতুন বর্ণনা"
    assert not MetadataVersion.objects.exists()


@pytest.mark.parametrize(
    "fields,field",
    [
        ({"title": "!!!"}, "title"),
        ({"alternative_names": ["!!!"]}, "alternative_names"),
        ({"social_image_url": "http://library.test/image.png"}, "social_image_url"),
        ({"state": "published"}, "state"),
        ({"summary": "x" * 20001}, "summary"),
        ({"record_type": "manual"}, "record_type"),
        ({"review_state": "approved"}, "review_state"),
        ({"manual_binding": "paper_back"}, "manual_binding"),
    ],
)
def test_invalid_edits_return_field_errors_without_writing(editor, fields, field):
    client, book = editor
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/",
        {**revision(book), **fields},
        format="json",
    )
    assert response.status_code == 400 and field in response.json()["field_errors"]
    assert not MetadataVersion.objects.exists()


def test_missing_revision_is_rejected(editor):
    client, book = editor
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/", {"summary": "বর্ণনা"}, format="json"
    )
    assert response.status_code == 400
    assert "expected_updated_at" in response.json()["field_errors"]
