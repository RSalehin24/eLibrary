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
def test_repeated_requests_reuse_canonical_submission_and_existing_job(monkeypatch):
    user = User.objects.create_user(email="repeat@example.com", password="strong-password-123")
    canonical_submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/repeat-book/",
        normalized_input=normalize_text("https://www.example.com/books/repeat-book/"),
        resolved_url="https://www.example.com/books/repeat-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.PROCESSING,
    )
    existing_job = ProcessingJob.objects.create(
        submission=canonical_submission,
        status=JobStatus.PROCESSING,
        queue_name="celery",
    )

    monkeypatch.setattr("apps.ingestion.services.submissions.capture_source_page_metadata", lambda url: None)

    duplicate_submission = create_submission_records(
        submitter=user,
        parsed_entries=[{"kind": "url", "value": "https://www.example.com/books/repeat-book/"}],
        auto_process=False,
    )[0]

    assert duplicate_submission.canonical_submission_id == canonical_submission.id
    assert duplicate_submission.status == SubmissionStatus.PROCESSING
    assert duplicate_submission.raw_payload["deduplicated"] is True

    returned_job = queue_submission(duplicate_submission)

    assert returned_job.id == existing_job.id
    assert ProcessingJob.objects.count() == 1


@pytest.mark.django_db
def test_new_url_submission_does_not_reuse_deleted_ready_submission(monkeypatch):
    user = User.objects.create_user(email="deleted-reuse@example.com", password="strong-password-123")
    deleted_book = Book.objects.create(title="মুছে ফেলা বই", state="soft_deleted", review_state="approved")
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())
    deleted_book.refresh_from_db()
    BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/deleted-book/",
        normalized_input=normalize_text("https://www.example.com/books/deleted-book/"),
        resolved_url="https://www.example.com/books/deleted-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.READY,
        linked_book=deleted_book,
    )

    monkeypatch.setattr("apps.ingestion.services.submissions.capture_source_page_metadata", lambda url: None)

    recreated_submission = create_submission_records(
        submitter=user,
        parsed_entries=[{"kind": "url", "value": "https://www.example.com/books/deleted-book/"}],
        auto_process=False,
    )[0]

    assert recreated_submission.linked_book_id is None
    assert recreated_submission.canonical_submission_id is None
    assert recreated_submission.status == SubmissionStatus.QUEUED
    assert recreated_submission.resolved_url == "https://www.example.com/books/deleted-book/"


@pytest.mark.django_db
def test_new_url_submission_does_not_reuse_failed_request(monkeypatch):
    user = User.objects.create_user(email="failed-reuse@example.com", password="strong-password-123")
    failed_submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/failed-book/",
        normalized_input=normalize_text("https://www.example.com/books/failed-book/"),
        resolved_url="https://www.example.com/books/failed-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.FAILED,
        error_message="Processing failed.",
    )

    monkeypatch.setattr("apps.ingestion.services.submissions.capture_source_page_metadata", lambda url: None)

    recreated_submission = create_submission_records(
        submitter=user,
        parsed_entries=[{"kind": "url", "value": "https://www.example.com/books/failed-book/"}],
        auto_process=False,
    )[0]

    assert recreated_submission.id != failed_submission.id
    assert recreated_submission.canonical_submission_id is None
    assert recreated_submission.status == SubmissionStatus.QUEUED


@pytest.mark.django_db
def test_retrying_deleted_submission_clears_reused_state_and_queues_recreation(client, monkeypatch):
    user = User.objects.create_user(email="retry-deleted@example.com", password="strong-password-123")
    url = (
        "https://www.example.com/books/"
        "%E0%A7%A8%E0%A7%A6%E0%A7%A6%E0%A7%A7-%E0%A6%86-%E0%A6%B8%E0%A7%8D%E0%A6%AA%E0%A7%87%E0%A6%B8-"
        "%E0%A6%93%E0%A6%A1%E0%A6%BF%E0%A6%B8%E0%A6%BF-%E0%A6%86%E0%A6%B0%E0%A7%8D%E0%A6%A5%E0%A6%BE%E0%A6%B0/"
    )
    deleted_book = Book.objects.create(title="২০০১ : আ স্পেস ওডিসি", state="soft_deleted", review_state="approved")
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())
    deleted_book.refresh_from_db()
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input=url,
        normalized_input=normalize_text(url),
        resolved_url=url,
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.READY,
        review_state=ReviewState.APPROVED,
        linked_book=deleted_book,
        duplicate_of_book=deleted_book,
        raw_payload={
            "served_from_database": True,
            "existing_book_source": "source_url",
            "linked_book_slug": deleted_book.slug,
        },
    )
    monkeypatch.setattr("apps.ingestion.services.submissions.dispatch_processing_job", lambda job, force=False: job)
    client.force_login(user)

    response = client.post(
        f"/api/ingestion/submissions/{submission.id}/retry/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 202
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.review_state == ReviewState.PENDING
    assert submission.linked_book_id is None
    assert submission.duplicate_of_book_id is None
    assert submission.raw_payload.get("served_from_database") is None
    assert submission.raw_payload.get("existing_book_source") is None
    assert submission.raw_payload.get("linked_book_slug") is None
    assert ProcessingJob.objects.filter(submission=submission, status=JobStatus.QUEUED).count() == 1
