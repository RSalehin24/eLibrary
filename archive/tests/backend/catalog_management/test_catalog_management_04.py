import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.db import connection
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.text import slugify

from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookContributor,
    BookSource,
    CATALOG_CODE_LENGTH,
    Category,
    Contributor,
    derive_category_catalog_code_from_book_code,
    derive_writer_catalog_code_from_book_code,
    GeneratedAsset,
    GeneratedAssetType,
    MetadataReview,
    MetadataVersion,
    Series,
)
from apps.catalog.services import get_or_create_category, get_or_create_contributor, get_or_create_series, replace_book_relations
from apps.ingestion.models import BookSubmission, DuplicateReview, ProcessingJob


@pytest.mark.django_db
def test_catalog_can_filter_books_created_by_current_user(client):
    owner = User.objects.create_user(email="owner@example.com", password="strong-password-123")
    other_user = User.objects.create_user(email="other@example.com", password="strong-password-123")
    owner_book = Book.objects.create(title="আমার বই", state="ready", review_state="approved")
    shared_book = Book.objects.create(title="শেয়ার্ড বই", state="ready", review_state="approved")
    other_book = Book.objects.create(title="অন্য বই", state="ready", review_state="approved")

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
    BookSubmission.objects.filter(pk=older_submission.pk).update(created_at=older_timestamp)
    BookSubmission.objects.filter(pk=newest_owner_submission.pk).update(created_at=newest_timestamp)

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
    user = User.objects.create_user(email="paged-reader@example.com", password="strong-password-123")
    Book.objects.create(title="আলফা বই", state="ready", review_state="approved")
    Book.objects.create(title="বিটা বই", state="ready", review_state="approved")
    third_book = Book.objects.create(title="গামা বই", state="ready", review_state="approved")
    client.force_login(user)

    response = client.get("/api/catalog/books/?record_type=all&sort=created_at&limit=2&page=2")

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
    user = User.objects.create_user(email="bangla-search-reader@example.com", password="strong-password-123")
    book = Book.objects.create(title="অ-আ-ক-খুনের কাঁটা", state="ready", review_state="approved")
    replace_book_relations(
        book,
        contributors=[{"name": "নারায়ণ সান্যাল", "role": "author"}],
        series_names=["পি. কে. বাসু - কাঁটা সিরিজ"],
        category_names=["গোয়েন্দা (ডিটেকটিভ)"],
    )
    client.force_login(user)

    title_response = client.get("/api/catalog/books/", {"record_type": "all", "q": "অ আ ক খুনের কাঁটা"})
    series_response = client.get(
        "/api/catalog/books/",
        {"record_type": "all", "series": "পি কে বাসু কাঁটা সিরিজ"},
    )
    category_response = client.get(
        "/api/catalog/books/",
        {"record_type": "all", "category": "গোয়েন্দা ডিটেকটিভ"},
    )

    assert title_response.status_code == 200
    assert {entry["slug"] for entry in title_response.json()} == {book.slug}
    assert series_response.status_code == 200
    assert {entry["slug"] for entry in series_response.json()} == {book.slug}
    assert category_response.status_code == 200
    assert {entry["slug"] for entry in category_response.json()} == {book.slug}


@pytest.mark.django_db
def test_catalog_book_list_avoids_loading_heavy_content_columns(client):
    user = User.objects.create_user(email="catalog-reader@example.com", password="strong-password-123")
    Book.objects.create(
        title="ভারী বই",
        state="ready",
        review_state="approved",
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
def test_metadata_editor_can_replace_book_epub_asset(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"

    editor = User.objects.create_user(email="epub-editor@example.com", password="strong-password-123")
    book = Book.objects.create(title="ইপাব বই", state="ready", review_state="approved")
    PermissionGrant.objects.create(user=editor, book=book, scope=PermissionScope.METADATA_EDIT)
    client.force_login(editor)

    asset = GeneratedAsset.objects.create(book=book, asset_type=GeneratedAssetType.EPUB, status="ready")
    asset.file.save("old.epub", ContentFile(b"old-bytes"), save=True)
    old_path = Path(asset.file.path)

    upload = SimpleUploadedFile("replacement.epub", b"new-epub-bytes", content_type="application/epub+zip")
    response = client.post(f"/api/catalog/books/{book.slug}/assets/epub/", data={"file": upload})

    assert response.status_code == 200
    asset.refresh_from_db()

    assert asset.status == "ready"
    assert asset.file_size == len(b"new-epub-bytes")
    assert asset.legacy_path == ""
    assert Path(asset.file.path).read_bytes() == b"new-epub-bytes"
    assert not old_path.exists()
    assert any(entry["asset_type"] == "epub" for entry in response.json()["assets"])


@pytest.mark.django_db
def test_metadata_editor_can_queue_book_regeneration_from_book_page(client, monkeypatch):
    editor = User.objects.create_user(email="reprocess-editor@example.com", password="strong-password-123")
    book = Book.objects.create(title="পুনর্জন্ম বই", state="ready", review_state="approved")
    PermissionGrant.objects.create(user=editor, book=book, scope=PermissionScope.METADATA_EDIT)
    BookSource.objects.create(
        book=book,
        source_url="https://www.example.com/books/reprocess-book/",
        normalized_source_url="https://www.example.com/books/reprocess-book/",
        source_title="পুনর্জন্ম বই",
    )
    client.force_login(editor)

    def fake_queue_reprocess_book(book_obj, actor=None):
        book_obj.state = "processing"
        book_obj.save(update_fields=["state", "updated_at"])
        submission = BookSubmission.objects.create(
            submitter=actor,
            input_type="url",
            original_input="https://www.example.com/books/reprocess-book/",
            normalized_input="https://www.example.com/books/reprocess-book/",
            resolved_url="https://www.example.com/books/reprocess-book/",
            resolution_status="resolved",
            resolution_confidence=1.0,
            status="queued",
            linked_book=book_obj,
        )
        job = ProcessingJob.objects.create(submission=submission, book=book_obj, job_type="reprocess", status="queued")
        return job, True

    monkeypatch.setattr("apps.catalog.views.queue_reprocess_book", fake_queue_reprocess_book)

    response = client.post(
        f"/api/catalog/books/{book.slug}/regenerate/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["created"] is True
    assert payload["job"]["job_type"] == "reprocess"
    assert payload["book"]["state"] == "processing"
    assert payload["book"]["latest_processing_job"]["status"] == "queued"
