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
def test_duplicate_review_list_defaults_to_pending_reviews(client):
    admin = User.objects.create_superuser(
        email="duplicate-list-admin@example.com",
        password="strong-password-123",
    )
    existing_book = Book.objects.create(
        title="ডুপ্লিকেট তালিকা বই",
        state="ready",
        review_state="approved",
    )
    pending_submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input="https://www.example.com/books/pending-duplicate/",
        normalized_input=normalize_text(
            "https://www.example.com/books/pending-duplicate/",
        ),
        resolved_url="https://www.example.com/books/pending-duplicate/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.DUPLICATE,
    )
    dismissed_submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input="https://www.example.com/books/dismissed-duplicate/",
        normalized_input=normalize_text(
            "https://www.example.com/books/dismissed-duplicate/",
        ),
        resolved_url="https://www.example.com/books/dismissed-duplicate/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    pending_review = DuplicateReview.objects.create(
        submission=pending_submission,
        existing_book=existing_book,
        status=DuplicateReviewStatus.PENDING,
    )
    dismissed_review = DuplicateReview.objects.create(
        submission=dismissed_submission,
        existing_book=existing_book,
        status=DuplicateReviewStatus.DISMISSED,
    )
    client.force_login(admin)

    response = client.get("/api/ingestion/duplicate-reviews/")

    assert response.status_code == 200
    payload = response.json()
    assert [entry["id"] for entry in payload] == [str(pending_review.id)]

    filtered_response = client.get("/api/ingestion/duplicate-reviews/?status=dismissed")

    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert [entry["id"] for entry in filtered_payload] == [str(dismissed_review.id)]


@pytest.mark.django_db
def test_duplicate_review_keep_new_queues_recreate_for_deleted_existing_book(client, settings, monkeypatch):
    settings.CELERY_TASK_ALWAYS_EAGER = False
    admin = User.objects.create_superuser(email="deleted-review-admin@example.com", password="strong-password-123")
    deleted_book = Book.objects.create(title="মুছে ফেলা বই", state="soft_deleted", review_state="approved")
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())
    deleted_book.refresh_from_db()
    submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input="https://www.example.com/books/deleted-book/",
        normalized_input=normalize_text("https://www.example.com/books/deleted-book/"),
        resolved_url="https://www.example.com/books/deleted-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.DUPLICATE,
        review_state="needs_review",
        linked_book=deleted_book,
        duplicate_of_book=deleted_book,
        raw_payload={"served_from_database": True, "linked_book_slug": deleted_book.slug},
    )
    review = DuplicateReview.objects.create(
        submission=submission,
        existing_book=deleted_book,
        detected_by="normalized_metadata",
        status=DuplicateReviewStatus.PENDING,
    )
    monkeypatch.setattr("apps.ingestion.services.submissions.dispatch_processing_job", lambda job, force=False: job)
    client.force_login(admin)

    response = client.post(
        f"/api/ingestion/duplicate-reviews/{review.id}/resolve/",
        data=json.dumps({"decision": "dismiss"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    review.refresh_from_db()
    submission.refresh_from_db()
    assert review.status == DuplicateReviewStatus.DISMISSED
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.review_state == "pending"
    assert submission.linked_book_id is None
    assert submission.duplicate_of_book_id is None
    assert submission.raw_payload.get("served_from_database") is None
    assert ProcessingJob.objects.filter(submission=submission, status=JobStatus.QUEUED).count() == 1


@pytest.mark.django_db
def test_public_submission_accepts_mixed_entries_and_reuses_existing_books(client):
    existing_book = Book.objects.create(title="সংরক্ষিত বই", state="ready", review_state="approved")
    BookSource.objects.create(
        book=existing_book,
        source_url="https://www.example.com/books/existing-book/",
        normalized_source_url="https://www.example.com/books/existing-book/",
        source_title="সংরক্ষিত বই",
    )

    response = client.post(
        "/api/ingestion/submissions/",
        data=json.dumps(
            {
                "entries": [
                    "https://www.example.com/books/existing-book/",
                    "সংরক্ষিত বই",
                ],
                "auto_process": True,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload) == 2
    reused_entry = next(entry for entry in payload if entry["input_type"] == "url")
    title_entry = next(entry for entry in payload if entry["input_type"] == "title")

    assert reused_entry["served_from_database"] is True
    assert reused_entry["linked_book_slug"] == existing_book.slug
    assert title_entry["served_from_database"] is False
    assert title_entry["linked_book_slug"] == ""
    assert title_entry["status"] in {"queued", "processing", "needs_review", "ready"}
    assert PreviewAccessSession.objects.count() == 0


@pytest.mark.django_db
def test_confirm_candidate_requires_manual_choice_for_ambiguous_title(client, monkeypatch):
    user = User.objects.create_user(email="reviewer@example.com", password="strong-password-123")
    client.force_login(user)

    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/sample-book-one/",
        title="স্যাম্পল বুক এক",
        author_line="লেখক",
        normalized_title=normalize_text("স্যাম্পল বুক এক"),
        normalized_display=normalize_text("স্যাম্পল বুক এক লেখক"),
    )
    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/sample-book-two/",
        title="স্যাম্পল বুক দুই",
        author_line="লেখক",
        normalized_title=normalize_text("স্যাম্পল বুক দুই"),
        normalized_display=normalize_text("স্যাম্পল বুক দুই লেখক"),
    )

    created = client.post(
        "/api/ingestion/submissions/",
        data=json.dumps(
            {
                "input_type": "title",
                "content": "স্যাম্পল বুক",
                "auto_process": False,
            }
        ),
        content_type="application/json",
    )
    assert created.status_code == 201
    payload = created.json()[0]
    assert payload["status"] == "needs_review"
    assert len(payload["candidates"]) == 2

    called = {}

    def fake_queue_submission(submission, actor=None):
        called["submission_id"] = str(submission.id)
        return ProcessingJob.objects.create(submission=submission)

    monkeypatch.setattr("apps.ingestion.views.queue_submission", fake_queue_submission)
    confirm = client.post(
        f"/api/ingestion/submissions/{payload['id']}/confirm-candidate/",
        data=json.dumps({"candidate_id": payload["candidates"][0]["id"]}),
        content_type="application/json",
    )

    assert confirm.status_code == 200
    assert called["submission_id"] == payload["id"]
    submission = BookSubmission.objects.get(pk=payload["id"])
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.resolution_status == "resolved"
