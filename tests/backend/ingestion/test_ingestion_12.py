import json

import pytest
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookContributor,
    Contributor,
)
from apps.ingestion.models import (
    BookSubmission,
    JobStatus,
    ProcessingJob,
    ResolutionStatus,
    SubmissionStatus,
)
from apps.ingestion.services.legacy_adapter import normalize_text
from apps.ingestion.services.submissions import (
    detect_metadata_duplicate,
)
from django.utils import timezone


@pytest.mark.django_db
def test_bulk_retry_requeues_unique_submission_targets(client, monkeypatch):
    user = User.objects.create_user(
        email="retry-bulk@example.com", password="strong-password-123"
    )
    canonical_submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/retry-bulk-root/",
        normalized_input=normalize_text(
            "https://www.example.com/books/retry-bulk-root/"
        ),
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
        normalized_input=normalize_text(
            "https://www.example.com/books/retry-bulk-root/"
        ),
        resolved_url="https://www.example.com/books/retry-bulk-root/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.FAILED,
        error_message="Duplicate failed.",
    )
    independent_submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/retry-bulk-independent/",
        normalized_input=normalize_text(
            "https://www.example.com/books/retry-bulk-independent/"
        ),
        resolved_url="https://www.example.com/books/retry-bulk-independent/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.FAILED,
        error_message="Independent failed.",
    )

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.resolution_and_queueing.dispatch_processing_job",
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
    assert (
        ProcessingJob.objects.filter(
            submission=canonical_submission, status=JobStatus.QUEUED
        ).count()
        == 1
    )
    assert (
        ProcessingJob.objects.filter(
            submission=independent_submission, status=JobStatus.QUEUED
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_resume_cancelled_job_requeues_submission(client, monkeypatch):
    user = User.objects.create_user(
        email="resume-cancelled@example.com", password="strong-password-123"
    )
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/resume-cancelled/",
        normalized_input=normalize_text(
            "https://www.example.com/books/resume-cancelled/"
        ),
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
        "apps.ingestion.services.submission_modules.resolution_and_queueing.dispatch_processing_job",
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
    user = User.objects.create_user(
        email="resume-cancelled-bulk@example.com", password="strong-password-123"
    )
    submission_one = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/bulk-resume-one/",
        normalized_input=normalize_text(
            "https://www.example.com/books/bulk-resume-one/"
        ),
        resolved_url="https://www.example.com/books/bulk-resume-one/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
        error_message="Stopped by user.",
    )
    submission_two = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/bulk-resume-two/",
        normalized_input=normalize_text(
            "https://www.example.com/books/bulk-resume-two/"
        ),
        resolved_url="https://www.example.com/books/bulk-resume-two/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.CANCELLED,
        error_message="Stopped by user.",
    )
    job_one = ProcessingJob.objects.create(
        submission=submission_one, status=JobStatus.CANCELLED, cancel_requested=False
    )
    job_two = ProcessingJob.objects.create(
        submission=submission_two, status=JobStatus.CANCELLED, cancel_requested=False
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.resolution_and_queueing.dispatch_processing_job",
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
    deleted_book = Book.objects.create(title="ম্যালিস", state="soft_deleted")
    contributor = Contributor.objects.create(name="সৈকত মুখোপাধ্যায়")
    BookContributor.objects.create(
        book=deleted_book, contributor=contributor, role="author"
    )
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())

    duplicate = detect_metadata_duplicate(
        {"book_title": "ম্যালিস", "author": "সৈকত মুখোপাধ্যায়"}
    )

    assert duplicate is None


@pytest.mark.django_db
def test_detect_metadata_duplicate_does_not_match_same_title_with_different_author():
    existing_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready")
    existing_author = Contributor.objects.create(name="কবি এক")
    BookContributor.objects.create(
        book=existing_book, contributor=existing_author, role="author"
    )

    duplicate = detect_metadata_duplicate(
        {"book_title": "শ্রেষ্ঠ কবিতা", "author": "কবি দুই"}
    )

    assert duplicate is None
