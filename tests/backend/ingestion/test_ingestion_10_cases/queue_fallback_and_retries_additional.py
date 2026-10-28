import pytest
from apps.ingestion.models import (
    BookSubmission,
    JobStatus,
    ProcessingJob,
    ResolutionStatus,
    SubmissionStatus,
)
from apps.ingestion.services.legacy_adapter import normalize_text
from apps.ingestion.services.submissions import (
    process_submission_job,
)


@pytest.mark.django_db
def test_process_submission_job_requeues_intermediate_failures_without_becoming_terminal(
    monkeypatch,
):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/retry-intermediate/",
        normalized_input=normalize_text(
            "https://www.example.com/books/retry-intermediate/"
        ),
        resolved_url="https://www.example.com/books/retry-intermediate/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.QUEUED,
        task_id="celery-retry-task",
        queue_name="celery",
    )

    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.retry_and_deduplication.capture_source_page_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.job_lifecycle.scrape_book",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("temporary scrape failure")
        ),
    )

    with pytest.raises(RuntimeError, match="temporary scrape failure"):
        process_submission_job(
            str(job.id),
            retry_count=1,
            task_id="celery-retry-task",
        )

    job.refresh_from_db()
    submission.refresh_from_db()
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 2
    assert job.task_id == "celery-retry-task"
    assert job.queue_name == "celery"
    assert "attempt 2 of 3" in job.last_error
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.error_message == ""
