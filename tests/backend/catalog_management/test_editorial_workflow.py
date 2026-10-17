import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, MetadataReview, MetadataVersion
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def editor():
    user = User.objects.create_user(email="editor@library.test")
    book = Book.objects.create(title="খসড়া বই", main_content_html="PRIVATE BODY")
    PermissionGrant.objects.create(
        user=user, scope=PermissionScope.METADATA_EDIT, book=book
    )
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


def test_scoped_editor_can_edit_review_publish_and_withdraw(editor):
    client, book = editor
    previous_slug = book.slug
    path = f"/api/v1/manage/books/{book.slug}/"
    response = client.patch(
        path,
        {
            **revision(book),
            "title": "পর্যালোচিত বই",
            "editorial_description": "মূল সম্পাদকীয় পরিচিতি",
            "alternative_names": ["Reviewed Book"],
            "indexing_eligible": True,
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["review_state"] == "pending"
    assert response.json()["editorial_reviewed_at"] is None
    assert "PRIVATE BODY" not in response.content.decode()
    book.refresh_from_db()
    assert book.slug != previous_slug
    assert MetadataVersion.objects.get(book=book).snapshot["title"] == "খসড়া বই"
    assert command(client, book, "publish").status_code == 200
    assert command(client, book, "review").status_code == 200
    assert MetadataReview.objects.get(book=book).reviewer.email == "editor@library.test"
    assert command(client, book, "publish").status_code == 200
    public = client.get(f"/api/v1/catalog/books/{previous_slug}/")
    assert public.status_code == 200
    assert public.json()["slug"] == book.slug
    assert public.json()["indexable"] is True
    assert public.json()["editorial_description"] == "মূল সম্পাদকীয় পরিচিতি"
    assert command(client, book, "withdraw").status_code == 200
    assert client.get(f"/api/v1/catalog/books/{previous_slug}/").status_code == 404


def test_published_metadata_is_visible_without_a_manual_review(editor):
    client, book = editor
    book.state = "published"
    book.review_state = "approved"
    book.editorial_description = "UNREVIEWED DESCRIPTION"
    book.alternative_names = ["UNREVIEWED ALIAS"]
    book.seo_title = "UNREVIEWED TITLE"
    book.save()
    response = client.get(f"/api/v1/catalog/books/{book.slug}/")
    assert response.status_code == 200
    assert response.json()["editorial_description"] == book.editorial_description
    assert response.json()["seo_title"] == book.seo_title
    assert response.json()["indexable"] is False
    assert response.json()["alternative_names"] == book.alternative_names


def test_stale_updates_and_commands_cannot_overwrite_a_newer_revision(editor):
    client, book = editor
    stale = revision(book)
    book.summary = "নতুন বর্ণনা"
    book.save()
    path = f"/api/v1/manage/books/{book.slug}/"
    response = client.patch(path, {**stale, "summary": "পুরোনো বর্ণনা"}, format="json")
    assert response.status_code == 409
    assert response.json()["code"] == "state_conflict"
    for action in ("review", "publish", "withdraw"):
        assert client.post(f"{path}{action}/", stale, format="json").status_code == 409
    book.refresh_from_db()
    assert book.summary == "নতুন বর্ণনা"
    assert not MetadataVersion.objects.exists()
    assert not MetadataReview.objects.exists()


def test_editing_a_published_book_keeps_it_visible_without_review(editor):
    client, book = editor
    book.state = "published"
    book.review_state = "approved"
    book.editorial_reviewed_at = timezone.now()
    book.save()
    path = f"/api/v1/manage/books/{book.slug}/"
    assert (
        client.patch(
            path, {**revision(book), "summary": "সংশোধিত"}, format="json"
        ).status_code
        == 200
    )
    public = client.get(f"/api/v1/catalog/books/{book.slug}/")
    assert public.status_code == 200
    assert public.json()["summary"] == "সংশোধিত"
    assert command(client, book, "review").status_code == 200
    assert client.get(f"/api/v1/catalog/books/{book.slug}/").status_code == 200


def test_another_book_cannot_be_read_or_changed_by_scoped_editor(editor):
    client, _ = editor
    other = Book.objects.create(title="অন্য বই")
    path = f"/api/v1/manage/books/{other.slug}/"
    assert client.get(path).status_code == 404
    assert (
        client.patch(
            path, {**revision(other), "title": "পরিবর্তিত"}, format="json"
        ).status_code
        == 404
    )
    for action in ("review", "publish", "withdraw"):
        assert command(client, other, action).status_code == 404
    assert APIClient().get(path).status_code == 403
    other.refresh_from_db()
    assert other.title == "অন্য বই"


@pytest.mark.parametrize(
    "fields,field",
    [
        ({"title": "!!!"}, "title"),
        ({"alternative_names": ["!!!"]}, "alternative_names"),
        ({"social_image_url": "http://library.test/image.png"}, "social_image_url"),
        ({"state": "published"}, "state"),
        ({"summary": "x" * 20001}, "summary"),
    ],
)
def test_invalid_edits_return_field_errors_without_writing(editor, fields, field):
    client, book = editor
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/",
        {**revision(book), **fields},
        format="json",
    )
    assert response.status_code == 400
    assert field in response.json()["field_errors"]
    assert not MetadataVersion.objects.exists()


def test_missing_revision_is_rejected(editor):
    client, book = editor
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/", {"summary": "বর্ণনা"}, format="json"
    )
    assert response.status_code == 400
    assert "expected_updated_at" in response.json()["field_errors"]
