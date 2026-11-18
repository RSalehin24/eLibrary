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
def test_public_submission_detail_and_confirm_candidate_are_available_without_login(client, monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="title",
        original_input="ম্যালিস",
        normalized_input=normalize_text("ম্যালিস"),
        resolution_status=ResolutionStatus.AMBIGUOUS,
        status=SubmissionStatus.NEEDS_REVIEW,
        review_state="needs_review",
        raw_payload={"submitted_publicly": True},
    )
    attempt = TitleResolutionAttempt.objects.create(
        submission=submission,
        query="ম্যালিস",
        normalized_query=normalize_text("ম্যালিস"),
        status=ResolutionStatus.AMBIGUOUS,
        confidence=0.92,
    )
    first_candidate = MatchCandidate.objects.create(
        resolution_attempt=attempt,
        rank=1,
        candidate_title="ম্যালিস",
        candidate_author="সৈকত মুখোপাধ্যায়",
        candidate_url="https://www.example.com/books/malice/",
        confidence=0.92,
    )
    MatchCandidate.objects.create(
        resolution_attempt=attempt,
        rank=2,
        candidate_title="ম্যালিস রিটার্নস",
        candidate_author="অন্য লেখক",
        candidate_url="https://www.example.com/books/malice-returns/",
        confidence=0.61,
    )

    detail = client.get(f"/api/ingestion/submissions/{submission.id}/")
    assert detail.status_code == 200
    assert len(detail.json()["candidates"]) == 2

    called = {}

    def fake_queue_submission(target_submission, actor=None):
        called["submission_id"] = str(target_submission.id)
        called["actor"] = actor
        return ProcessingJob.objects.create(submission=target_submission)

    monkeypatch.setattr("apps.ingestion.views.queue_submission", fake_queue_submission)
    confirm = client.post(
        f"/api/ingestion/submissions/{submission.id}/confirm-candidate/",
        data=json.dumps({"candidate_id": str(first_candidate.id)}),
        content_type="application/json",
    )

    assert confirm.status_code == 200
    assert called["submission_id"] == str(submission.id)
    assert called["actor"] is None
    submission.refresh_from_db()
    assert submission.resolved_url == "https://www.example.com/books/malice/"
    assert submission.resolution_status == ResolutionStatus.RESOLVED
    assert submission.status == SubmissionStatus.QUEUED


@pytest.mark.django_db
def test_public_submission_action_links_create_guest_preview_session(tmp_path, client):
    book = Book.objects.create(title="গেস্ট বুক", state="ready", review_state="approved")
    epub_path = Path(tmp_path) / "guest-book.epub"
    html_path = Path(tmp_path) / "guest-book.html"
    epub_path.write_bytes(b"epub")
    html_path.write_text("<html></html>", encoding="utf-8")
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(epub_path),
        content_type="application/epub+zip",
        file_size=epub_path.stat().st_size,
    )
    GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.HTML,
        status=GeneratedAssetStatus.READY,
        legacy_path=str(html_path),
        content_type="text/html",
        file_size=html_path.stat().st_size,
    )
    submission = BookSubmission.objects.create(
        input_type="title",
        original_input="গেস্ট বুক",
        normalized_input=normalize_text("গেস্ট বুক"),
        linked_book=book,
        resolved_url="https://www.example.com/books/guest-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_confidence=1.0,
        status=SubmissionStatus.READY,
        raw_payload={"submitted_publicly": True},
    )

    response = client.post(
        f"/api/ingestion/submissions/{submission.id}/action-links/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["launch_url"]
    assert payload["epub_download_url"]
    assert payload["html_preview_url"]
    preview_session = PreviewAccessSession.objects.get(source_submission=submission)
    assert preview_session.user is None

    manifest = client.get(payload["manifest_url"].replace("http://testserver", ""))
    assert manifest.status_code == 200
    manifest_payload = manifest.json()
    assert manifest_payload["reading_session_url"] == ""
    assert manifest_payload["bookmarks_url"] == ""
    assert manifest_payload["reading_session"] is None
    assert manifest_payload["bookmarks"] == []

    guest_session_state = client.get(f"/api/access/reader/{preview_session.token}/session/")
    guest_bookmarks = client.get(f"/api/access/reader/{preview_session.token}/bookmarks/")
    assert guest_session_state.status_code == 403
    assert guest_bookmarks.status_code == 403


@pytest.mark.django_db
def test_submission_detail_marks_soft_deleted_linked_book_as_deleted(client):
    user = User.objects.create_user(email="deleted-submission@example.com", password="strong-password-123")
    book = Book.objects.create(title="মুছে ফেলা বই", state="soft_deleted", review_state="approved")
    Book.objects.filter(pk=book.pk).update(deleted_at=timezone.now())
    book.refresh_from_db()
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="title",
        original_input="মুছে ফেলা বই",
        normalized_input=normalize_text("মুছে ফেলা বই"),
        linked_book=book,
        resolved_url="https://www.example.com/books/deleted-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_confidence=1.0,
        status=SubmissionStatus.READY,
    )
    client.force_login(user)

    response = client.get(f"/api/ingestion/submissions/{submission.id}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "deleted"
    assert payload["linked_book_deleted"] is True
    assert payload["linked_book_slug"] == ""
    assert payload["linked_book"]["title"] == "মুছে ফেলা বই"


@pytest.mark.django_db
def test_submission_action_links_reject_soft_deleted_linked_book(client):
    user = User.objects.create_user(email="deleted-action-links@example.com", password="strong-password-123")
    book = Book.objects.create(title="মুছে ফেলা বই", state="soft_deleted", review_state="approved")
    Book.objects.filter(pk=book.pk).update(deleted_at=timezone.now())
    book.refresh_from_db()
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="title",
        original_input="মুছে ফেলা বই",
        normalized_input=normalize_text("মুছে ফেলা বই"),
        linked_book=book,
        resolved_url="https://www.example.com/books/deleted-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_confidence=1.0,
        status=SubmissionStatus.READY,
    )
    client.force_login(user)

    response = client.post(
        f"/api/ingestion/submissions/{submission.id}/action-links/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 410
    assert response.json()["detail"] == "This book was deleted."


@pytest.mark.django_db
def test_deleting_queued_submission_marks_it_deleted_and_retry_queues_it_again(client, monkeypatch):
    user = User.objects.create_user(email="deleted-request@example.com", password="strong-password-123")
    source_url = "https://www.example.com/books/deleted-request/"
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input=source_url,
        normalized_input=normalize_text(source_url),
        resolved_url=source_url,
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.QUEUED,
        task_id="queued-delete-task",
        queue_name="celery",
    )

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.revoke_processing_task",
        lambda task_id, terminate=False: None,
    )
    monkeypatch.setattr("apps.ingestion.services.submissions.dispatch_processing_job", lambda job, force=False: job)
    client.force_login(user)

    delete_response = client.delete(f"/api/ingestion/submissions/{submission.id}/")

    assert delete_response.status_code == 204
    submission.refresh_from_db()
    job.refresh_from_db()
    assert submission.status == SubmissionStatus.DELETED
    assert job.status == JobStatus.CANCELLED

    retry_response = client.post(
        f"/api/ingestion/submissions/{submission.id}/retry/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert retry_response.status_code == 202
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.QUEUED
    assert ProcessingJob.objects.filter(submission=submission, status=JobStatus.QUEUED).exists()
