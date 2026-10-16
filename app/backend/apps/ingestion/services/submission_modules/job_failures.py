from .job_lifecycle import (
    MAX_PROCESSING_JOB_ATTEMPTS,
    PROCESSING_RETRY_MESSAGE_TEMPLATE,
    JobStatus,
    SubmissionStatus,
    logger,
    record_job_log,
    timezone,
)
from .retry_and_deduplication import (
    requeue_processing_job,
    sync_deduplicated_submissions,
)


def handle_submission_failure(job, exc, reprocess_book):
    submission = job.submission
    logger.exception("Submission processing failed", extra={"submission_id": str(job.submission_id)})
    next_retry_count = int(job.retry_count or 0) + 1
    should_retry = next_retry_count < MAX_PROCESSING_JOB_ATTEMPTS

    if should_retry:
        requeue_processing_job(
            job,
            retry_count=next_retry_count,
            message=PROCESSING_RETRY_MESSAGE_TEMPLATE.format(
                attempt=next_retry_count,
                max_attempts=MAX_PROCESSING_JOB_ATTEMPTS,
            ),
            preserve_dispatch_state=bool(job.task_id),
        )
        raise exc

    submission.status = SubmissionStatus.FAILED
    submission.error_message = str(exc)
    submission.save(update_fields=["status", "error_message", "updated_at"])
    sync_deduplicated_submissions(submission)
    if reprocess_book is not None:
        previous_book_state = job.payload.get("previous_book_state")
        if previous_book_state:
            reprocess_book.state = previous_book_state
            reprocess_book.save(update_fields=["state", "updated_at"])
    job.status = JobStatus.FAILED
    job.task_id = ""
    job.queue_name = ""
    job.last_error = str(exc)
    job.finished_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "task_id",
            "queue_name",
            "last_error",
            "finished_at",
            "updated_at",
        ]
    )
    record_job_log(job, "error", "Submission processing failed.", {"error": str(exc)})
    raise exc
