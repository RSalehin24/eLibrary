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
def test_bulk_retry_requeues_unique_submission_targets(client, monkeypatch):
    user = User.objects.create_user(email="retry-bulk@example.com", password="strong-password-123")
    canonical_submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/retry-bulk-root/",
        normalized_input=normalize_text("https://www.example.com/books/retry-bulk-root/"),
        resolved_url="https://www.example.com/books/retry-bulk-root/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.FAILED,
        error_message="Root failed.",
    )
    duplicate_submission = BookSubmission.objects.create(
        submitter=user,
        canonical_submission=canonical_submission,
        input_type="url",
        original_input="https://www.example.com/books/retry-bulk-root/",
        normalized_input=normalize_text("https://www.example.com/books/retry-bulk-root/"),
        resolved_url="https://www.example.com/books/retry-bulk-root/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.FAILED,
        error_message="Duplicate failed.",
    )
    independent_submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/retry-bulk-independent/",
        normalized_input=normalize_text("https://www.example.com/books/retry-bulk-independent/"),
        resolved_url="https://www.example.com/books/retry-bulk-independent/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.FAILED,
        error_message="Independent failed.",
    )

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.dispatch_processing_job",
        lambda queued_job, force=False: queued_job,
    )

    client.force_login(user)
    response = client.post(
        "/api/ingestion/submissions/bulk-retry/",
        data=json.dumps(
            {
                "ids": [
                    str(canonical_submission.id),
                    str(duplicate_submission.id),
                    str(independent_submission.id),
                ]
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["queued_count"] == 2
    assert payload["skipped_invalid"] == 0
    assert payload["skipped_duplicate_targets"] == 1
    assert payload["skipped_missing"] == 0

    canonical_submission.refresh_from_db()
    independent_submission.refresh_from_db()
    assert canonical_submission.status == SubmissionStatus.QUEUED
    assert independent_submission.status == SubmissionStatus.QUEUED
    assert ProcessingJob.objects.filter(submission=canonical_submission, status=JobStatus.QUEUED).count() == 1
    assert ProcessingJob.objects.filter(submission=independent_submission, status=JobStatus.QUEUED).count() == 1


@pytest.mark.django_db
def test_resume_cancelled_job_requeues_submission(client, monkeypatch):
    user = User.objects.create_user(email="resume-cancelled@example.com", password="strong-password-123")
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/resume-cancelled/",
        normalized_input=normalize_text("https://www.example.com/books/resume-cancelled/"),
        resolved_url="https://www.example.com/books/resume-cancelled/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
        error_message="Stopped by user.",
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.CANCELLED,
        cancel_requested=False,
        task_id="old-task-id",
        queue_name="celery",
        last_error="Stopped by user.",
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.dispatch_processing_job",
        lambda queued_job, force=False: queued_job,
    )

    client.force_login(user)
    response = client.post(
        f"/api/ingestion/jobs/{job.id}/resume/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 202
    job.refresh_from_db()
    submission.refresh_from_db()
    assert job.status == JobStatus.QUEUED
    assert job.cancel_requested is False
    assert job.task_id == ""
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.error_message == ""


@pytest.mark.django_db
def test_bulk_resume_requeues_cancelled_jobs(client, monkeypatch):
    user = User.objects.create_user(email="resume-cancelled-bulk@example.com", password="strong-password-123")
    submission_one = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/bulk-resume-one/",
        normalized_input=normalize_text("https://www.example.com/books/bulk-resume-one/"),
        resolved_url="https://www.example.com/books/bulk-resume-one/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
        error_message="Stopped by user.",
    )
    submission_two = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/bulk-resume-two/",
        normalized_input=normalize_text("https://www.example.com/books/bulk-resume-two/"),
        resolved_url="https://www.example.com/books/bulk-resume-two/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
        error_message="Stopped by user.",
    )
    job_one = ProcessingJob.objects.create(submission=submission_one, status=JobStatus.CANCELLED, cancel_requested=False)
    job_two = ProcessingJob.objects.create(submission=submission_two, status=JobStatus.CANCELLED, cancel_requested=False)
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.dispatch_processing_job",
        lambda queued_job, force=False: queued_job,
    )

    client.force_login(user)
    response = client.post(
        "/api/ingestion/jobs/bulk-resume/",
        data=json.dumps({"ids": [str(job_one.id), str(job_two.id)]}),
        content_type="application/json",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["resumed_count"] == 2
    assert payload["skipped_invalid"] == 0

    job_one.refresh_from_db()
    job_two.refresh_from_db()
    submission_one.refresh_from_db()
    submission_two.refresh_from_db()
    assert job_one.status == JobStatus.QUEUED
    assert job_two.status == JobStatus.QUEUED
    assert submission_one.status == SubmissionStatus.QUEUED
    assert submission_two.status == SubmissionStatus.QUEUED


@pytest.mark.django_db
def test_detect_metadata_duplicate_ignores_deleted_books():
    deleted_book = Book.objects.create(title="ম্যালিস", state="soft_deleted", review_state="approved")
    contributor = Contributor.objects.create(name="সৈকত মুখোপাধ্যায়")
    BookContributor.objects.create(book=deleted_book, contributor=contributor, role="author")
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())

    duplicate = detect_metadata_duplicate({"book_title": "ম্যালিস", "author": "সৈকত মুখোপাধ্যায়"})

    assert duplicate is None


@pytest.mark.django_db
def test_detect_metadata_duplicate_does_not_match_same_title_with_different_author():
    existing_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready", review_state="approved")
    existing_author = Contributor.objects.create(name="কবি এক")
    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")

    duplicate = detect_metadata_duplicate({"book_title": "শ্রেষ্ঠ কবিতা", "author": "কবি দুই"})

    assert duplicate is None
