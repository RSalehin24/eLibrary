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
def test_processing_search_matches_percent_encoded_source_titles(client):
    admin = User.objects.create_superuser(email="search-admin@example.com", password="strong-password-123")
    client.force_login(admin)

    encoded_slug = quote("খেয়া-রবীন্দ্রনাথ-ঠাকুর", safe="")
    source_url = f"https://www.example.com/books/{encoded_slug}/"
    submission = BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.USER,
        original_input=source_url,
        normalized_input=normalize_text(source_url),
        resolved_url=source_url,
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
    )
    job = ProcessingJob.objects.create(submission=submission, status=JobStatus.CANCELLED, job_type="create")
    existing_book = Book.objects.create(title="খেয়া", state="ready", review_state="approved")
    review = DuplicateReview.objects.create(
        submission=submission,
        existing_book=existing_book,
        status=DuplicateReviewStatus.PENDING,
    )

    for query in ("খেয়া", "খেয়া রবীন্দ্রনাথ ঠাকুর"):
        submissions_response = client.get(f"/api/ingestion/submissions/?q={query}")
        jobs_response = client.get(f"/api/ingestion/jobs/?q={query}")
        reviews_response = client.get(f"/api/ingestion/duplicate-reviews/?q={query}")

        assert submissions_response.status_code == 200
        assert [entry["id"] for entry in submissions_response.json()] == [str(submission.id)]
        assert jobs_response.status_code == 200
        assert [entry["id"] for entry in jobs_response.json()] == [str(job.id)]
        assert reviews_response.status_code == 200
        assert [entry["id"] for entry in reviews_response.json()] == [str(review.id)]


@pytest.mark.django_db
def test_processing_manager_can_stop_queued_job(client, monkeypatch):
    admin = User.objects.create_superuser(email="stop-job-admin@example.com", password="strong-password-123")
    client.force_login(admin)
    submission = BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.USER,
        original_input="https://www.example.com/books/queued-book/",
        normalized_input=normalize_text("https://www.example.com/books/queued-book/"),
        resolved_url="https://www.example.com/books/queued-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.QUEUED,
        task_id="queued-task",
        queue_name="celery",
    )

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.revoke_processing_task",
        lambda task_id, terminate=False: None,
    )

    response = client.post(f"/api/ingestion/jobs/{job.id}/stop/", data=json.dumps({}), content_type="application/json")

    assert response.status_code == 200
    job.refresh_from_db()
    submission.refresh_from_db()
    assert job.status == JobStatus.CANCELLED
    assert submission.status == SubmissionStatus.CANCELLED


@pytest.mark.django_db
def test_processing_manager_can_stop_processing_job(client, monkeypatch):
    admin = User.objects.create_superuser(email="stop-processing-job-admin@example.com", password="strong-password-123")
    client.force_login(admin)
    submission = BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.USER,
        original_input="https://www.example.com/books/processing-book/",
        normalized_input=normalize_text("https://www.example.com/books/processing-book/"),
        resolved_url="https://www.example.com/books/processing-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.PROCESSING,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.PROCESSING,
        task_id="processing-task",
        queue_name="celery",
        cancel_requested=False,
    )

    revoke_calls = []

    def fake_revoke(task_id, terminate=False):
        revoke_calls.append({"task_id": task_id, "terminate": terminate})

    monkeypatch.setattr("apps.ingestion.services.submissions.revoke_processing_task", fake_revoke)

    response = client.post(f"/api/ingestion/jobs/{job.id}/stop/", data=json.dumps({}), content_type="application/json")

    assert response.status_code == 200
    job.refresh_from_db()
    submission.refresh_from_db()
    assert revoke_calls == [{"task_id": "processing-task", "terminate": True}]
    assert job.status == JobStatus.CANCELLED
    assert job.cancel_requested is False
    assert submission.status == SubmissionStatus.CANCELLED


@pytest.mark.django_db
def test_processing_manager_can_stop_catalog_curation_run(client, monkeypatch):
    admin = User.objects.create_superuser(email="stop-run-admin@example.com", password="strong-password-123")
    client.force_login(admin)
    run = CatalogCurationRun.objects.create(
        trigger="manual",
        mode="pending",
        status=JobStatus.QUEUED,
        refresh_catalog=True,
        refresh_max_pages=80,
        requested_by=admin,
        task_id="queued-run-task",
        queue_name="celery",
    )

    monkeypatch.setattr("apps.ingestion.services.curation.revoke_curation_task", lambda task_id: None)

    response = client.post(
        f"/api/ingestion/catalog/curation-runs/{run.id}/stop/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 200
    run.refresh_from_db()
    assert run.status == JobStatus.CANCELLED


@pytest.mark.django_db
def test_due_catalog_automation_queues_one_scheduled_run_per_day(monkeypatch):
    now = timezone.localtime(timezone.now()).replace(
        hour=10,
        minute=0,
        second=0,
        microsecond=0,
    )
    settings_obj = get_catalog_automation_settings()
    settings_obj.enabled = True
    settings_obj.daily_run_time = now.replace(hour=1, minute=0).time()
    settings_obj.mode = "pending"
    settings_obj.refresh_max_pages = 10
    settings_obj.save()

    def fake_create_catalog_curation_run(**kwargs):
        return CatalogCurationRun.objects.create(
            trigger=kwargs["trigger"],
            mode=kwargs["mode"],
            status="queued",
            refresh_catalog=kwargs["refresh_catalog"],
            refresh_max_pages=kwargs["refresh_max_pages"],
        )

    monkeypatch.setattr("apps.ingestion.services.curation.create_catalog_curation_run", fake_create_catalog_curation_run)

    result = run_due_catalog_automation(now=now)
    second_result = run_due_catalog_automation(now=now)

    assert result["ran"] is True
    assert CatalogCurationRun.objects.filter(trigger="scheduled").count() == 1
    assert second_result["ran"] is False
    assert second_result["reason"] == "already_ran"


@pytest.mark.django_db
def test_weekly_catalog_automation_waits_until_the_next_week(monkeypatch):
    now = timezone.localtime(timezone.now()).replace(hour=10, minute=0, second=0, microsecond=0)
    settings_obj = get_catalog_automation_settings()
    settings_obj.enabled = True
    settings_obj.daily_run_time = now.replace(hour=9, minute=0).time()
    settings_obj.frequency = CatalogAutomationFrequency.WEEKLY
    settings_obj.save()
    type(settings_obj).objects.filter(pk=settings_obj.pk).update(updated_at=now - timedelta(days=10))
    settings_obj.refresh_from_db()

    latest_run = CatalogCurationRun.objects.create(
        trigger="scheduled",
        mode="pending",
        status="succeeded",
        refresh_catalog=True,
        refresh_max_pages=10,
    )
    CatalogCurationRun.objects.filter(pk=latest_run.pk).update(created_at=now - timedelta(days=3))

    result = run_due_catalog_automation(now=now)

    assert result["ran"] is False
    assert result["reason"] == "already_ran"
