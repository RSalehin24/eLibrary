from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope, ReadingSession
from apps.accounts.models import User
from apps.catalog.models import Book, BookCategory, Category, SavedBook, UserBook
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
URL = "/api/v1/me/books/"


def personal_fixture():
    actor = User.objects.create_user(email="personal-reader@library.test")
    client = APIClient()
    client.force_authenticate(actor)
    book = Book.objects.create(title="পাঠকের অনুমোদিত বই", state="published")
    return actor, client, book


def test_saving_is_idempotent_private_and_never_assigns_ownership():
    actor, client, book = personal_fixture()
    path = f"{URL}{book.slug}/saved/"
    assert client.get(path).json() == {"saved": False}
    for _ in range(2):
        assert client.put(path, {"saved": True}, format="json").json() == {
            "saved": True
        }
    assert SavedBook.objects.count() == 1 and not UserBook.objects.exists()
    response = client.get(URL, {"view": "saved"})
    assert response["Cache-Control"] == "private, no-store"
    assert [entry["id"] for entry in response.json()["entries"]] == [str(book.pk)]
    client.force_authenticate(
        User.objects.create_user(email="other-personal@library.test")
    )
    assert client.get(path).json() == {"saved": False}
    assert client.get(URL, {"view": "saved"}).json()["entries"] == []
    client.force_authenticate(actor)
    assert client.put(path, {"saved": False}, format="json").status_code == 200
    assert not SavedBook.objects.exists()


def test_saved_records_cannot_reveal_a_withdrawn_or_ungranted_draft():
    actor, client, book = personal_fixture()
    SavedBook.objects.create(user=actor, book=book)
    book.state = "draft"
    book.save()
    assert client.get(URL, {"view": "saved"}).json()["entries"] == []
    assert client.get(f"{URL}{book.slug}/").status_code == 404
    grant = PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.READ_DURABLE
    )
    assert len(client.get(URL, {"view": "saved"}).json()["entries"]) == 1
    grant.is_active = False
    grant.save()
    assert client.get(URL, {"view": "saved"}).json()["entries"] == []


def test_recent_books_sort_by_own_reading_time_and_bind_cursors_to_view():
    actor, client, first = personal_fixture()
    second = Book.objects.create(title="পরে তৈরি আগে পড়া", state="published")
    for book in [first, second]:
        ReadingSession.objects.create(user=actor, book=book)
    ReadingSession.objects.filter(user=actor, book=second).update(
        last_opened_at=timezone.now() - timedelta(days=1)
    )
    response = client.get(URL, {"view": "recent", "limit": 1}).json()
    assert response["entries"][0]["id"] == str(first.pk)
    next_page = client.get(
        URL, {"view": "recent", "limit": 1, "cursor": response["next_cursor"]}
    ).json()
    assert next_page["entries"][0]["id"] == str(second.pk) and not next_page["has_more"]
    assert (
        client.get(
            URL, {"view": "saved", "cursor": response["next_cursor"]}
        ).status_code
        == 400
    )
    assert client.get(URL, {"view": "other"}).status_code == 400


def test_granted_view_filters_expired_grants_and_respects_category_scopes():
    actor, client, book = personal_fixture()
    category = Category.objects.create(name="অনুমোদিত বিভাগ")
    BookCategory.objects.create(book=book, category=category)
    other = Book.objects.create(title="মেয়াদ শেষ", state="published")
    PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.READ_DURABLE, category=category
    )
    PermissionGrant.objects.create(
        user=actor,
        scope=PermissionScope.READ_ONCE,
        book=other,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert [
        entry["id"] for entry in client.get(URL, {"view": "granted"}).json()["entries"]
    ] == [str(book.pk)]
    assert client.get(URL).json()["entries"] == []


def test_saved_book_session_mutations_require_csrf():
    actor, _, book = personal_fixture()
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(actor)
    path = f"{URL}{book.slug}/saved/"
    assert client.put(path, {"saved": True}, format="json").status_code == 403
    assert not SavedBook.objects.exists()
