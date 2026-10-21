from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    Category,
    Contributor,
    GeneratedAsset,
    SavedBook,
    UserBook,
)
from apps.catalog.reading.list_controls import book_list_controls
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PATH = "/api/v1/me/book-controls/"


@pytest.fixture
def controls_reader(tmp_path):
    user = User.objects.create_user(email="list-controls@example.test")
    book = Book.objects.create(title="List controls", state="published")
    file = tmp_path / "ready.epub"
    file.write_bytes(b"fixture")
    GeneratedAsset.objects.create(
        book=book, asset_type="epub", status="ready", legacy_path=str(file)
    )
    client = APIClient()
    client.force_authenticate(user)
    return client, user, book


def test_list_controls_matches_reader_permission_and_saved_state(controls_reader):
    client, user, book = controls_reader
    SavedBook.objects.create(user=user, book=book)
    response = client.get(PATH, {"slugs": [book.slug, book.slug]})
    assert response.status_code == 200
    assert response.json()["entries"] == [
        {"slug": book.slug, "saved": True, "can_send_kindle": False}
    ]
    UserBook.objects.create(user=user, book=book)
    expected = client.get(f"/api/v1/reading/books/{book.slug}/access/").json()[
        "can_send_kindle"
    ]
    assert (
        expected
        and client.get(PATH, {"slugs": [book.slug]}).json()["entries"][0][
            "can_send_kindle"
        ]
        == expected
    )
    assert "no-store" in response["Cache-Control"]


@pytest.mark.parametrize(
    "scope", ["book", "category", "contributor", "global", "admin"]
)
def test_list_controls_matches_targeted_kindle_grants(controls_reader, scope):
    client, user, book = controls_reader
    values = {"user": user, "scope": PermissionScope.SEND_KINDLE}
    if scope == "book":
        values["book"] = book
    elif scope == "category":
        category = Category.objects.create(name="Granted category")
        BookCategory.objects.create(book=book, category=category)
        values["category"] = category
    elif scope == "contributor":
        contributor = Contributor.objects.create(name="Granted writer")
        BookContributor.objects.create(
            book=book, contributor=contributor, role="author"
        )
        values["contributor"] = contributor
    elif scope == "admin":
        values["scope"] = PermissionScope.ADMIN_FULL_CONTROL
    grant = PermissionGrant.objects.create(**values)
    assert client.get(PATH, {"slugs": [book.slug]}).json()["entries"][0][
        "can_send_kindle"
    ]
    grant.expires_at = timezone.now() - timedelta(seconds=1)
    grant.save()
    assert not client.get(PATH, {"slugs": [book.slug]}).json()["entries"][0][
        "can_send_kindle"
    ]


def test_list_controls_omit_private_books_and_disable_unavailable_kindle_files(
    controls_reader,
):
    client, user, book = controls_reader
    private = Book.objects.create(title="Unpublished private record")
    paper = Book.objects.create(
        title="Paper record", state="published", record_type="manual"
    )
    UserBook.objects.create(user=user, book=book)
    GeneratedAsset.objects.filter(book=book).update(legacy_path="/missing.epub")
    data = client.get(PATH, {"slugs": [book.slug, private.slug, paper.slug]}).json()[
        "entries"
    ]
    assert {entry["slug"] for entry in data} == {book.slug, paper.slug}
    assert not any(entry["can_send_kindle"] for entry in data)
    book.source_quality_state = "quarantined"
    book.save()
    assert not client.get(PATH, {"slugs": [book.slug]}).json()["entries"][0][
        "can_send_kindle"
    ]


@pytest.mark.parametrize(
    "slugs", [[], ["../private"], ["%2Fprivate"], ["a.b"], ["x" * 256], ["x"] * 101]
)
def test_list_controls_bound_and_validate_every_slug(controls_reader, slugs):
    assert controls_reader[0].get(PATH, {"slugs": slugs}).status_code == 400


def test_list_controls_query_count_is_bounded(controls_reader):
    _, user, book = controls_reader
    other = [
        Book.objects.create(title=f"Batch record {index}", state="published")
        for index in range(8)
    ]
    with CaptureQueriesContext(connection) as one:
        assert len(book_list_controls(user, [book.slug])) == 1
    with CaptureQueriesContext(connection) as several:
        result = book_list_controls(user, [book.slug, *(entry.slug for entry in other)])
    assert len(result) == 9
    # Three existing scope checks, then one book query and one asset prefetch.
    assert len(one) == len(several) == 5


def test_list_controls_blocks_anonymous_and_required_totp_accounts(controls_reader):
    _, user, book = controls_reader
    client = Client()
    assert client.get(PATH, {"slugs": [book.slug]}).status_code == 403
    user.totp_required = True
    user.save()
    client.force_login(user)
    assert client.get(PATH, {"slugs": [book.slug]}).status_code == 403
