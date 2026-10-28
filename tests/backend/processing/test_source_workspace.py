from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, BookSource
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import BackgroundJob
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

pytestmark = pytest.mark.django_db
SOURCES = "/api/v1/manage/sources/"


@pytest.mark.parametrize("chaptered", [False, True])
def test_source_detail_reports_content_counts_without_exposing_book_text(
    client, processor, chaptered
):
    entry = source_entry(700)
    body = "<p>private-book-text</p>"
    items = [{"title": "Chapter", "content": body}] if chaptered else []
    book = link_book(entry, {"main_content_html": body, "content_items": items})
    response = client.get(SOURCES + f"{entry.pk}/")
    assert response.status_code == 200
    summary = response.json()["content_summary"]
    assert summary == {
        "body_character_count": 34 if chaptered else 17,
        "chapter_count": int(chaptered),
        "check_completeness": not chaptered,
        "verification": None,
    }
    assert "private-book-text" not in response.content.decode()
    assert client.get(SOURCES).json()["entries"][0]["content_summary"] is None
    book.refresh_from_db()
    assert book.state == "draft"


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


def test_source_book_editing_requires_current_administrator_authority(
    client, processor
):
    entry = source_entry(1)
    book = link_book(entry)
    endpoint = SOURCES + f"{entry.pk}/"
    detail = client.get(endpoint).json()
    assert detail["book"]["id"] == str(book.pk) and detail["can_edit_book"] is False
    PermissionGrant.objects.create(
        user=processor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    assert client.get(endpoint).json()["can_edit_book"] is False
    processor.is_staff = True
    processor.save()
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
    update_projection = (
        f'("{SourceCatalogEntry._meta.db_table}"."raw_data" -> '
        "'source_update') AS \"source_update\""
    )
    for query in queries.captured_queries:
        selected = query["sql"].replace(update_projection, "")
        assert '"main_content_html"' not in selected
        assert '"raw_data"' not in selected


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


@pytest.mark.parametrize(
    "state",
    [
        "queued",
        "running",
        "retry_wait",
        "paused",
        "needs_attention",
        "succeeded",
        "failed",
    ],
)
def test_source_rows_and_details_report_the_actual_active_job_state(
    client, processor, state
):
    entry = source_entry(901)
    operation = BackgroundJob.objects.create(
        source_record=entry,
        kind="process_source",
        state=state,
        requested_by=processor,
        available_at=timezone.now(),
    )
    expected = None if state in {"succeeded", "failed"} else state
    for result in (
        client.get(SOURCES).json()["entries"][0],
        client.get(SOURCES + f"{entry.pk}/").json(),
    ):
        assert result["active_operation_state"] == expected
        assert result["active_operation_id"] == (
            str(operation.pk) if expected else None
        )
        assert result["latest_operation_id"] == str(operation.pk)
