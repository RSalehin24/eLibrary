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
    process_catalog_curation_run,
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
def test_processing_manager_can_queue_deleted_catalog_entry_for_recreation(client, monkeypatch):
    admin = User.objects.create_superuser(email="catalog-recreate-admin@example.com", password="strong-password-123")
    client.force_login(admin)
    deleted_book = Book.objects.create(title="Deleted Book", state="soft_deleted", review_state="pending")
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())
    deleted_book.refresh_from_db()
    entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/deleted-book/",
        title="Deleted Book",
        author_line="Writer",
        normalized_title=normalize_text("Deleted Book"),
        normalized_display=normalize_text("Deleted Book Writer"),
    )
    BookSource.objects.create(
        book=deleted_book,
        source_url=entry.source_url,
        normalized_source_url=entry.source_url,
        source_title=entry.title,
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
        data=json.dumps({"ids": [str(entry.id)]}),
        content_type="application/json",
    )

    assert response.status_code == 202
    assert response.json()["queued_creates"] == 1
    assert response.json()["skipped_deleted"] == 0
    assert queued_entries == [{"kind": "url", "value": entry.source_url}]


@pytest.mark.django_db
def test_catalog_automation_recreates_stopped_catalog_entry_without_local_book(
    monkeypatch,
):
    entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/stopped-missing-book/",
        title="Stopped Missing Book",
        author_line="Writer",
        normalized_title=normalize_text("Stopped Missing Book"),
        normalized_display=normalize_text("Stopped Missing Book Writer"),
    )
    BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.USER,
        original_input=entry.source_url,
        normalized_input=normalize_text(entry.source_url),
        resolved_url=entry.source_url,
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
    )
    run = CatalogCurationRun.objects.create(
        trigger="scheduled",
        mode="pending",
        status="queued",
        refresh_catalog=False,
        refresh_max_pages=1,
    )
    queued_entries = []

    def fake_create_submission_records(
        *, submitter, parsed_entries, auto_process, origin
    ):
        queued_entries.extend(parsed_entries)
        assert submitter is None
        assert auto_process is True
        assert origin == SubmissionOrigin.AUTOMATION
        return []

    monkeypatch.setattr(
        "apps.ingestion.services.curation.create_submission_records",
        fake_create_submission_records,
    )

    result = process_catalog_curation_run(run.id)

    assert result.status == JobStatus.SUCCEEDED
    assert result.summary["queued_creates"] == 1
    assert result.summary["queued_updates"] == 0
    assert result.summary["status_counts"]["stopped"] == 1
    assert queued_entries == [{"kind": "url", "value": entry.source_url}]


@pytest.mark.django_db
def test_catalog_automation_reprocesses_stopped_catalog_entry_with_local_book(
    monkeypatch,
):
    entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/stopped-local-book/",
        title="Stopped Local Book",
        author_line="Writer",
        normalized_title=normalize_text("Stopped Local Book"),
        normalized_display=normalize_text("Stopped Local Book Writer"),
    )
    book = Book.objects.create(
        title="Stopped Local Book",
        state=LifecycleState.READY,
        review_state=ReviewState.PENDING,
    )
    BookSource.objects.create(
        book=book,
        source_url=entry.source_url,
        normalized_source_url=entry.source_url,
        source_title=entry.title,
    )
    submission = BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.CURATION,
        original_input=entry.source_url,
        normalized_input=normalize_text(entry.source_url),
        resolved_url=entry.source_url,
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
        linked_book=book,
    )
    ProcessingJob.objects.create(
        submission=submission,
        book=book,
        status=JobStatus.CANCELLED,
    )
    run = CatalogCurationRun.objects.create(
        trigger="scheduled",
        mode="pending",
        status="queued",
        refresh_catalog=False,
        refresh_max_pages=1,
    )
    requeued_books = []

    def fake_queue_reprocess_book(book, actor=None, origin=SubmissionOrigin.USER):
        requeued_books.append((book.id, actor, origin))
        return object(), True

    monkeypatch.setattr(
        "apps.ingestion.services.curation.queue_reprocess_book",
        fake_queue_reprocess_book,
    )

    result = process_catalog_curation_run(run.id)

    assert result.status == JobStatus.SUCCEEDED
    assert result.summary["queued_creates"] == 0
    assert result.summary["queued_updates"] == 1
    assert result.summary["status_counts"]["stopped"] == 1
    assert requeued_books == [(book.id, None, SubmissionOrigin.AUTOMATION)]


@pytest.mark.django_db
def test_sync_assets_marks_book_for_review_when_epub_is_missing(tmp_path):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/missing-epub/",
        normalized_input=normalize_text("https://www.example.com/books/missing-epub/"),
        resolved_url="https://www.example.com/books/missing-epub/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.PROCESSING,
    )
    job = ProcessingJob.objects.create(submission=submission, status=JobStatus.PROCESSING)
    book = Book.objects.create(title="Missing EPUB", state="ready", review_state="pending")
    html_path = tmp_path / "book.html"
    html_path.write_text("<html><body>ok</body></html>", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing generated assets: EPUB"):
        sync_assets(
            book,
            job,
            {
                "book_title": "Missing EPUB",
                "output_folder": str(tmp_path),
                "cover": "",
            },
        )

    book.refresh_from_db()
    assert book.state == "needs_review"
    assert book.review_state == "needs_review"
    assert GeneratedAsset.objects.get(book=book, asset_type=GeneratedAssetType.HTML).status == GeneratedAssetStatus.READY
    assert GeneratedAsset.objects.get(book=book, asset_type=GeneratedAssetType.EPUB).status == GeneratedAssetStatus.FAILED
