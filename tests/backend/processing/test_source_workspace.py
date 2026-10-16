from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, BookSource
from apps.ingestion.models import SourceCatalogEntry
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

pytestmark = pytest.mark.django_db
SOURCES = "/api/v1/manage/sources/"


@pytest.fixture
def processor(client):
    user = User.objects.create_user(email="source-processor@library.test")
    PermissionGrant.objects.create(user=user, scope=PermissionScope.PROCESSING_MANAGE)
    client.force_login(user)
    return user


def source_entry(number):
    return SourceCatalogEntry.objects.create(
        source_url=f"https://source.library.test/books/{number}/",
        title=f"উৎসের বই {number}",
        author_line="বাংলা লেখক",
        normalized_title=f"উৎসের বই {number}",
        normalized_display=f"উৎসের বই {number} বাংলা লেখক",
        raw_data={"cookie": "never-return", "html": "private-source-body"},
    )


def link_book(entry, values=None):
    book = Book.objects.create(title=entry.title, **(values or {}))
    BookSource.objects.create(
        book=book, source_url=entry.source_url, normalized_source_url=entry.source_url
    )
    return book


def test_reader_and_scoped_processor_cannot_access_sources(client):
    user = User.objects.create_user(email="source-reader@library.test")
    book = Book.objects.create(title="নির্দিষ্ট বই")
    PermissionGrant.objects.create(
        user=user, book=book, scope=PermissionScope.PROCESSING_MANAGE
    )
    client.force_login(user)
    entry = source_entry(1)
    assert (
        client.get(SOURCES).status_code
        == client.get(SOURCES + f"{entry.pk}/").status_code
        == 403
    )


def test_source_lists_are_private_paginated_and_exclude_raw_payloads(client, processor):
    for number in range(51):
        source_entry(number)
    response = client.get(SOURCES)
    assert response.status_code == 200 and len(response.json()["entries"]) == 50
    assert response.json()["pagination"] == {"page": 1, "limit": 50, "total_count": 51}
    assert len(client.get(SOURCES, {"page": 2}).json()["entries"]) == 1
    assert (
        response["Cache-Control"] == "private, no-store"
        and response["X-Robots-Tag"] == "noindex"
    )
    assert (
        "never-return" not in response.content.decode()
        and "private-source-body" not in response.content.decode()
    )


@pytest.mark.parametrize(
    "parameters", [{"page": 0}, {"limit": 101}, {"q": "a" * 201}, {"status": "unknown"}]
)
def test_invalid_source_parameters_return_field_errors(client, processor, parameters):
    response = client.get(SOURCES, parameters)
    assert response.status_code == 400 and response.json()["field_errors"]


def test_source_status_filters_apply_in_the_database(client, processor):
    unlinked, linked, removed = [source_entry(number) for number in range(3)]
    link_book(linked)
    link_book(removed, {"deleted_at": timezone.now()})
    for status, expected in (
        ("unlinked", unlinked),
        ("linked", linked),
        ("removed", removed),
    ):
        entries = client.get(SOURCES, {"status": status}).json()["entries"]
        assert [entry["id"] for entry in entries] == [str(expected.pk)]
    assert len(client.get(SOURCES, {"q": "বাংলা লেখক"}).json()["entries"]) == 3


def test_source_book_editing_uses_scoped_metadata_authorization(client, processor):
    entry = source_entry(1)
    book = link_book(entry)
    endpoint = SOURCES + f"{entry.pk}/"
    detail = client.get(endpoint).json()
    assert detail["book"]["id"] == str(book.pk) and detail["can_edit_book"] is False
    PermissionGrant.objects.create(
        user=processor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    assert client.get(endpoint).json()["can_edit_book"] is True
    book.soft_delete()
    assert client.get(endpoint).json()["can_edit_book"] is False


def test_one_hundred_source_records_keep_queries_and_payloads_bounded(
    client, processor, django_assert_max_num_queries
):
    for number in range(100):
        entry = source_entry(number)
        link_book(entry, {"main_content_html": "private-book-body" * 100})
    with django_assert_max_num_queries(8), CaptureQueriesContext(connection) as queries:
        response = client.get(SOURCES, {"limit": 100})
    assert len(response.json()["entries"]) == 100
    assert "private-book-body" not in response.content.decode()
    assert not any(
        '"main_content_html"' in query["sql"] or '"raw_data"' in query["sql"]
        for query in queries.captured_queries
    )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://user:secret@source.library.test/book/",
        "https://source.library.test/\nbook/",
        "https://[bad/book/",
        "https://source.library.test:invalid/book/",
    ],
)
def test_unsafe_source_links_are_not_exposed_as_hrefs(client, processor, url):
    entry = source_entry(uuid4())
    entry.source_url = url
    entry.save()
    assert client.get(SOURCES + f"{entry.pk}/").json()["source_url"] is None


def test_source_display_links_omit_credentials_in_queries_and_fragments(
    client, processor
):
    entry = source_entry(1)
    entry.source_url += "?token=private#secret"
    entry.save()
    response = client.get(SOURCES + f"{entry.pk}/")
    assert response.json()["source_url"] == "https://source.library.test/books/1/"
    assert "private" not in response.content.decode()


def test_missing_source_record_returns_an_explicit_not_found(client, processor):
    response = client.get(SOURCES + f"{uuid4()}/")
    assert response.status_code == 404 and response.json()["code"] == "not_found"
