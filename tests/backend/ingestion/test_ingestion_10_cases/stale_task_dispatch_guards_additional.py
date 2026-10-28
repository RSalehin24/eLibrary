import pytest
from apps.ingestion.models import (
    BookSubmission,
    JobStatus,
    ProcessingJob,
    ResolutionStatus,
    SubmissionStatus,
)
from apps.ingestion.services.legacy_adapter import normalize_text
from apps.ingestion.services.submissions import dispatch_processing_job
from django.utils import timezone


@pytest.mark.django_db
def test_dispatch_processing_job_returns_failed_job_after_engine_execution_error(
    monkeypatch, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/eager-job/",
        normalized_input=normalize_text("https://www.example.com/books/eager-job/"),
        resolved_url="https://www.example.com/books/eager-job/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(submission=submission, status=JobStatus.QUEUED)

    def fake_apply_async(job_id, **_kwargs):
        task_id = ProcessingJob.objects.get(pk=job_id).task_id
        eager_job = ProcessingJob.objects.get(pk=job_id)
        eager_job.status = JobStatus.FAILED
        eager_job.task_id = task_id
        eager_job.queue_name = "celery"
        eager_job.last_error = "eager-job-failure"
        eager_job.finished_at = timezone.now()
        eager_job.save(
            update_fields=[
                "status",
                "task_id",
                "queue_name",
                "last_error",
                "finished_at",
                "updated_at",
            ]
        )
        eager_job.submission.status = SubmissionStatus.FAILED
        eager_job.submission.error_message = "eager-job-failure"
        eager_job.submission.save(
            update_fields=["status", "error_message", "updated_at"]
        )
        raise RuntimeError("eager-job-failure")

    monkeypatch.setattr("apps.ingestion.engine.dispatch.dispatch_job", fake_apply_async)
    monkeypatch.setattr(
        "apps.ingestion.services.submission_modules.processing_job_runner.process_submission_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("inline fallback should not rerun eager job failures")
        ),
    )

    result = dispatch_processing_job(job)

    job.refresh_from_db()
    submission.refresh_from_db()
    assert result.id == job.id
    assert job.status == JobStatus.FAILED
    assert job.queue_name == "celery"
    assert job.task_id
    assert submission.status == SubmissionStatus.FAILED
