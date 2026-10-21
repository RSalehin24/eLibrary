import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, SavedBook, UserBook
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def personal_detail_fixture():
    actor = User.objects.create_user(email="personal-detail-navigation@example.test")
    book = Book.objects.create(title="ব্যক্তিগত সংশ্লিষ্ট বই")
    client = APIClient()
    client.force_authenticate(actor)
    return actor, book, client


def test_grant_only_detail_selects_granted_without_changing_all_feed():
    actor, book, client = personal_detail_fixture()
    grant = PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.READ_DURABLE
    )
    response = client.get(f"/api/v1/me/books/{book.slug}/")
    assert response.status_code == 200
    assert response.json()["library_view"] == "granted"
    assert response["Cache-Control"] == "private, no-store"
    assert client.get("/api/v1/me/books/", {"view": "all"}).json()["entries"] == []
    assert (
        client.get("/api/v1/me/books/", {"view": "granted"}).json()["entries"][0][
            "slug"
        ]
        == book.slug
    )
    grant.is_active = False
    grant.save()
    assert client.get(f"/api/v1/me/books/{book.slug}/").status_code == 404


@pytest.mark.parametrize("membership", ["owned", "saved"])
def test_existing_all_feed_members_keep_all_as_the_direct_detail_default(membership):
    actor, book, client = personal_detail_fixture()
    if membership == "owned":
        UserBook.objects.create(user=actor, book=book)
    else:
        PermissionGrant.objects.create(
            user=actor, book=book, scope=PermissionScope.READ_DURABLE
        )
        SavedBook.objects.create(user=actor, book=book)
    response = client.get(f"/api/v1/me/books/{book.slug}/")
    assert response.status_code == 200
    assert response.json()["library_view"] == "all"


def test_library_context_does_not_expose_another_accounts_private_record():
    actor, book, client = personal_detail_fixture()
    UserBook.objects.create(user=actor, book=book)
    client.force_authenticate(
        User.objects.create_user(email="personal-detail-other@example.test")
    )
    assert client.get(f"/api/v1/me/books/{book.slug}/").status_code == 404
    book.state = "published"
    book.save()
    public = APIClient().get(f"/api/v1/catalog/books/{book.slug}/")
    assert public.status_code == 200
    assert "library_view" not in public.json()
