import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pytest
import requests
from django.db import IntegrityError
from django.utils import timezone

from apps.access.models import PreviewAccessSession
from apps.accounts.models import User
from apps.catalog.models import Book, BookContributor, BookSource, Category, Contributor, GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType, Series
from apps.common.models import LifecycleState, ReviewState
from apps.ingestion.models import (
    CatalogAutomationFrequency,
    BookSubmission,
    CatalogCurationRun,
    DuplicateReview,
    DuplicateReviewStatus,
    JobStatus,
    MatchCandidate,
    ProcessingJob,
    ResolutionStatus,
    SourceCatalogEntry,
    SourceCatalogRefreshState,
    SourceCatalogRefreshStatus,
    SubmissionOrigin,
    SubmissionStatus,
    TitleResolutionAttempt,
)
from apps.ingestion.services.curation import (
    get_catalog_automation_settings,
    next_catalog_automation_run_at,
    run_due_catalog_automation,
    source_catalog_entry_snapshots,
)
from apps.ingestion.pipeline import scraper as legacy_scraper
from apps.ingestion.services.legacy_adapter import normalize_text
from apps.ingestion.services.legacy_adapter import normalize_source_url
from apps.ingestion.services.normalization import (
    clean_extracted_dedication_html,
    extract_main_content_segments,
    extract_front_matter_entries,
    normalize_scraped_book,
    promote_leading_front_matter,
    split_leading_front_sections,
)
from apps.ingestion.services.resolution import CATALOG_URL, TitleResolver, get_with_host_fallback
from apps.ingestion.services.submissions import (
    create_submission_records,
    detect_metadata_duplicate,
    find_exact_existing_book,
    process_submission_job,
    queue_submission,
    sync_assets,
)
from apps.ingestion.tasks import process_submission_task
from apps.catalog.services import find_existing_book_by_source_url


@pytest.mark.django_db
def test_long_source_urls_can_be_stored_across_ingestion_and_catalog_models():
    long_slug = "source-book-" + ("extended-path-" * 20)
    long_url = f"https://www.example.com/books/{long_slug}/"
    book = Book.objects.create(title="Long URL Book", state="ready", review_state="pending")

    source_entry = SourceCatalogEntry.objects.create(
        source_url=long_url,
        title="Long URL Book",
        author_line="Writer",
        normalized_title=normalize_text("Long URL Book"),
        normalized_display=normalize_text("Long URL Book Writer"),
    )
    source = BookSource.objects.create(
        book=book,
        source_url=long_url,
        normalized_source_url=long_url,
        source_title="Long URL Book",
    )
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input=long_url,
        normalized_input=normalize_text(long_url),
        resolved_url=long_url,
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    attempt = TitleResolutionAttempt.objects.create(
        submission=submission,
        query="Long URL Book",
        normalized_query=normalize_text("Long URL Book"),
        status=ResolutionStatus.RESOLVED,
        resolved_url=long_url,
    )
    candidate = MatchCandidate.objects.create(
        resolution_attempt=attempt,
        rank=1,
        candidate_title="Long URL Book",
        candidate_author="Writer",
        candidate_url=long_url,
        confidence=0.98,
    )

    assert source_entry.source_url == long_url
    assert source.normalized_source_url == long_url
    assert submission.resolved_url == long_url
    assert attempt.resolved_url == long_url
    assert candidate.candidate_url == long_url


@pytest.mark.django_db
def test_source_catalog_entry_snapshots_mark_new_and_ready_books():
    missing_entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/missing-book/",
        title="Missing Book",
        author_line="Writer One",
        raw_data={"category": "Mystery"},
        normalized_title=normalize_text("Missing Book"),
        normalized_display=normalize_text("Missing Book Writer One"),
    )
    ready_entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/ready-book/",
        title="Ready Book",
        author_line="Writer Two",
        normalized_title=normalize_text("Ready Book"),
        normalized_display=normalize_text("Ready Book Writer Two"),
    )
    ready_book = Book.objects.create(title="Ready Book", state="ready", review_state="pending")
    BookSource.objects.create(
        book=ready_book,
        source_url=ready_entry.source_url,
        normalized_source_url=ready_entry.source_url,
        source_title=ready_entry.title,
    )
    GeneratedAsset.objects.create(book=ready_book, asset_type=GeneratedAssetType.HTML, status=GeneratedAssetStatus.READY)
    GeneratedAsset.objects.create(book=ready_book, asset_type=GeneratedAssetType.EPUB, status=GeneratedAssetStatus.READY)
    ready_book.categories.add(Category.objects.create(name="Novel"))

    snapshots, summary = source_catalog_entry_snapshots(SourceCatalogEntry.objects.order_by("title"))
    by_url = {snapshot["source_url"]: snapshot for snapshot in snapshots}

    assert by_url[missing_entry.source_url]["curation_status"] == "new"
    assert by_url[missing_entry.source_url]["categories"] == "Mystery"
    assert by_url[ready_entry.source_url]["curation_status"] == "ready"
    assert by_url[ready_entry.source_url]["categories"] == "Novel"
    assert summary["new"] == 1
    assert summary["ready"] == 1


@pytest.mark.django_db
def test_source_catalog_entry_snapshots_preserve_results_when_processed_in_small_chunks(monkeypatch):
    monkeypatch.setattr(
        "apps.ingestion.services.curation_support.catalog_entries.SOURCE_LOOKUP_CHUNK_SIZE",
        1,
    )
    missing_entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/chunked-missing-book/",
        title="Chunked Missing Book",
        author_line="Writer One",
        raw_data={"category": "Mystery"},
        normalized_title=normalize_text("Chunked Missing Book"),
        normalized_display=normalize_text("Chunked Missing Book Writer One"),
    )
    ready_entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/chunked-ready-book/",
        title="Chunked Ready Book",
        author_line="Writer Two",
        normalized_title=normalize_text("Chunked Ready Book"),
        normalized_display=normalize_text("Chunked Ready Book Writer Two"),
    )
    ready_book = Book.objects.create(
        title="Chunked Ready Book",
        state="ready",
        review_state="pending",
    )
    BookSource.objects.create(
        book=ready_book,
        source_url=ready_entry.source_url,
        normalized_source_url=ready_entry.source_url,
        source_title=ready_entry.title,
    )
    GeneratedAsset.objects.create(
        book=ready_book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
    )
    GeneratedAsset.objects.create(
        book=ready_book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
    )
    ready_book.categories.add(Category.objects.create(name="Novel"))

    snapshots, summary = source_catalog_entry_snapshots(
        SourceCatalogEntry.objects.order_by("title")
    )
    by_url = {snapshot["source_url"]: snapshot for snapshot in snapshots}

    assert by_url[missing_entry.source_url]["curation_status"] == "new"
    assert by_url[ready_entry.source_url]["curation_status"] == "ready"
    assert summary["new"] == 1
    assert summary["ready"] == 1


@pytest.mark.django_db
def test_source_catalog_entry_snapshots_surface_failed_creation_before_local_book_exists():
    entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/failed-book/",
        title="Failed Book",
        author_line="Writer",
        normalized_title=normalize_text("Failed Book"),
        normalized_display=normalize_text("Failed Book Writer"),
    )
    submission = BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.CURATION,
        original_input=entry.source_url,
        normalized_input=normalize_text(entry.source_url),
        resolved_url=entry.source_url,
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.FAILED,
        error_message="Missing generated assets: EPUB.",
    )
    ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.FAILED,
        last_error="Missing generated assets: EPUB.",
    )

    snapshots, summary = source_catalog_entry_snapshots(SourceCatalogEntry.objects.filter(pk=entry.pk))

    assert snapshots[0]["curation_status"] == "failed"
    assert snapshots[0]["latest_submission_status"] == "failed"
    assert snapshots[0]["latest_job_status"] == "failed"
    assert summary["failed"] == 1


@pytest.mark.django_db
def test_processing_manager_can_queue_selected_catalog_entries_for_creation(client, monkeypatch):
    admin = User.objects.create_superuser(email="catalog-create-admin@example.com", password="strong-password-123")
    client.force_login(admin)
    new_entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/new-book/",
        title="New Book",
        author_line="Writer",
        normalized_title=normalize_text("New Book"),
        normalized_display=normalize_text("New Book Writer"),
    )
    queued_entries = []

    def fake_create_submission_records(*, submitter, parsed_entries, auto_process, origin):
        queued_entries.extend(parsed_entries)
        assert submitter == admin
        assert auto_process is True
        assert origin == SubmissionOrigin.CURATION
        return []

    monkeypatch.setattr("apps.ingestion.views.create_submission_records", fake_create_submission_records)

    response = client.post(
        "/api/ingestion/catalog/entries/create-books/",
        data=json.dumps({"ids": [str(new_entry.id)]}),
        content_type="application/json",
    )

    assert response.status_code == 202
    assert response.json()["queued_creates"] == 1
    assert queued_entries == [{"kind": "url", "value": new_entry.source_url}]


@pytest.mark.django_db
def test_find_existing_book_by_source_url_ignores_soft_deleted_books():
    book = Book.objects.create(title="Deleted source book", state="soft_deleted", review_state="pending")
    Book.objects.filter(pk=book.pk).update(deleted_at=timezone.now())
    book.refresh_from_db()
    BookSource.objects.create(
        book=book,
        source_url="https://www.example.com/books/deleted-source-book/",
        normalized_source_url="httpswwwexamplecombooksdeletedsourcebook",
    )

    existing = find_existing_book_by_source_url("httpswwwexamplecombooksdeletedsourcebook")

    assert existing is None
