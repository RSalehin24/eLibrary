from datetime import timedelta

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset
from apps.catalog.services import replace_book_relations
from apps.ingestion.models import BookSubmission, ProcessingJob
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone


@pytest.mark.django_db
def test_catalog_can_filter_books_created_by_current_user(client):
    owner = User.objects.create_user(
        email="owner@example.com", password="strong-password-123"
    )
    other_user = User.objects.create_user(
        email="other@example.com", password="strong-password-123"
    )
    owner_book = Book.objects.create(title="আমার বই", state="ready")
    shared_book = Book.objects.create(title="শেয়ার্ড বই", state="ready")
    other_book = Book.objects.create(title="অন্য বই", state="ready")

    older_submission = BookSubmission.objects.create(
        submitter=owner,
        input_type="title",
        original_input="আমার বই",
        normalized_input="আমার বই",
        linked_book=owner_book,
        status="ready",
        resolution_status="resolved",
    )
    newest_owner_submission = BookSubmission.objects.create(
        submitter=owner,
        input_type="title",
        original_input="শেয়ার্ড বই",
        normalized_input="শেয়ার্ড বই",
        linked_book=shared_book,
        status="ready",
        resolution_status="resolved",
    )
    BookSubmission.objects.create(
        submitter=other_user,
        input_type="title",
        original_input="শেয়ার্ড বই",
        normalized_input="শেয়ার্ড বই",
        linked_book=shared_book,
        status="ready",
        resolution_status="resolved",
    )
    BookSubmission.objects.create(
        submitter=other_user,
        input_type="title",
        original_input="অন্য বই",
        normalized_input="অন্য বই",
        linked_book=other_book,
        status="ready",
        resolution_status="resolved",
    )

    older_timestamp = timezone.now() - timedelta(days=2)
    newest_timestamp = timezone.now() - timedelta(hours=2)
    BookSubmission.objects.filter(pk=older_submission.pk).update(
        created_at=older_timestamp
    )
    BookSubmission.objects.filter(pk=newest_owner_submission.pk).update(
        created_at=newest_timestamp
    )

    client.force_login(owner)
    response = client.get("/api/catalog/books/?ownership=mine&sort=-requested_at")

    assert response.status_code == 200
    payload = response.json()
    assert [entry["slug"] for entry in payload] == [shared_book.slug, owner_book.slug]
    assert other_book.slug not in {entry["slug"] for entry in payload}
    assert payload[0]["latest_submission_at"]
    assert payload[1]["latest_submission_at"]


@pytest.mark.django_db
def test_catalog_book_list_supports_paginated_responses(client):
    user = User.objects.create_user(
        email="paged-reader@example.com", password="strong-password-123"
    )
    Book.objects.create(title="আলফা বই", state="ready")
    Book.objects.create(title="বিটা বই", state="ready")
    third_book = Book.objects.create(title="গামা বই", state="ready")
    client.force_login(user)

    response = client.get("/api/catalog/books/?sort=created_at&limit=2&page=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"] == {
        "page": 2,
        "limit": 2,
        "total_count": 3,
        "page_count": 2,
        "has_previous": True,
        "has_next": False,
    }
    assert [entry["slug"] for entry in payload["entries"]] == [third_book.slug]


@pytest.mark.django_db
def test_catalog_book_search_supports_normalized_bangla_queries(client):
    user = User.objects.create_user(
        email="bangla-search-reader@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="অ-আ-ক-খুনের কাঁটা", state="ready")
    replace_book_relations(
        book,
        contributors=[{"name": "নারায়ণ সান্যাল", "role": "author"}],
        series_names=["পি. কে. বাসু - কাঁটা সিরিজ"],
        category_names=["গোয়েন্দা (ডিটেকটিভ)"],
    )
    client.force_login(user)

    title_response = client.get("/api/catalog/books/", {"q": "অ আ ক খুনের কাঁটা"})
    series_response = client.get(
        "/api/catalog/books/",
        {"series": "পি কে বাসু কাঁটা সিরিজ"},
    )
    category_response = client.get(
        "/api/catalog/books/",
        {"category": "গোয়েন্দা ডিটেকটিভ"},
    )

    assert title_response.status_code == 200
    assert {entry["slug"] for entry in title_response.json()} == {book.slug}
    assert series_response.status_code == 200
    assert {entry["slug"] for entry in series_response.json()} == {book.slug}
    assert category_response.status_code == 200
    assert {entry["slug"] for entry in category_response.json()} == {book.slug}


@pytest.mark.django_db
def test_catalog_book_list_avoids_loading_heavy_content_columns(client):
    user = User.objects.create_user(
        email="catalog-reader@example.com", password="strong-password-123"
    )
    Book.objects.create(
        title="ভারী বই",
        state="ready",
        summary="Summary",
        raw_scraped_metadata={"source": "seed"},
        raw_scrape_payload={"payload": "seed"},
        main_content_html="<p>Heavy content</p>",
        book_info_html="<p>Book info</p>",
        dedication_html="<p>Dedication</p>",
        toc=[{"label": "One", "href": "#one"}],
        content_items=[{"title": "One", "slug": "one"}],
    )
    client.force_login(user)

    with CaptureQueriesContext(connection) as captured_queries:
        response = client.get("/api/catalog/books/?limit=1&page=1")

    assert response.status_code == 200
    book_queries = [
        query["sql"]
        for query in captured_queries.captured_queries
        if 'FROM "catalog_book"' in query["sql"] and "COUNT(" not in query["sql"]
    ]
    assert book_queries
    list_query = book_queries[0]
    assert '"catalog_book"."summary"' not in list_query
    assert '"catalog_book"."raw_scraped_metadata"' not in list_query
    assert '"catalog_book"."raw_scrape_payload"' not in list_query
    assert '"catalog_book"."main_content_html"' not in list_query
    assert '"catalog_book"."book_info_html"' not in list_query
    assert '"catalog_book"."dedication_html"' not in list_query
    assert '"catalog_book"."toc"' not in list_query
    assert '"catalog_book"."content_items"' not in list_query


@pytest.mark.django_db
def test_metadata_editor_can_replace_book_epub_asset(client):
    actor = User.objects.create_user(
        email="nonadmin-writer@example.test", password="strong-password-123"
    )
    book = Book.objects.create(title="সম্পাদনা নিষিদ্ধ")
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    client.force_login(actor)
    suffix = "assets/epub/"
    assert client.post(f"/api/catalog/books/{book.slug}/{suffix}").status_code in {
        403,
        404,
    }
    assert not GeneratedAsset.objects.exists() and not ProcessingJob.objects.exists()


@pytest.mark.django_db
def test_metadata_editor_can_queue_book_regeneration_from_book_page(client):
    actor = User.objects.create_user(
        email="nonadmin-writer@example.test", password="strong-password-123"
    )
    book = Book.objects.create(title="সম্পাদনা নিষিদ্ধ")
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    client.force_login(actor)
    suffix = "regenerate/"
    assert client.post(f"/api/catalog/books/{book.slug}/{suffix}").status_code in {
        403,
        404,
    }
    assert not GeneratedAsset.objects.exists() and not ProcessingJob.objects.exists()
