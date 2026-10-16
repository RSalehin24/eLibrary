def dispatch_processing_job(job, force=False, attempt_offset=None):
    from apps.ingestion.engine.dispatch import dispatch_job

    from .job_lifecycle import (
        MAX_PROCESSING_JOB_ATTEMPTS,
        JobStatus,
        logger,
        record_job_log,
        uuid4,
    )
    from .processing_job_runner import process_submission_job

    job.refresh_from_db(fields=["status", "task_id", "queue_name", "cancel_requested", "updated_at"])
    if job.status == JobStatus.CANCELLED or job.cancel_requested:
        return job
    if not force and job.status == JobStatus.QUEUED and job.task_id:
        return job
    resolved_attempt_offset = max(
        int(job.retry_count or 0),
        int(attempt_offset or 0),
    )

    assigned_job_id = str(uuid4())
    job.task_id = assigned_job_id
    job.queue_name = "engine"
    job.save(update_fields=["task_id", "queue_name", "updated_at"])

    try:
        dispatch_job(
            job_id=str(job.id),
            job_type=job.job_type,
            handler="process_submission",
            attempt_offset=resolved_attempt_offset,
        )
    except Exception as exc:
        job.refresh_from_db()
        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job
        logger.warning("Engine dispatch failed, falling back to inline processing", exc_info=True)
        job.task_id = ""
        job.queue_name = "inline-fallback"
        job.last_error = f"Engine dispatch failed: {exc}"
        job.save(update_fields=["task_id", "queue_name", "last_error", "updated_at"])
        record_job_log(
            job,
            "warning",
            "Engine dispatch failed, processing inline instead.",
            {"error": str(exc)},
        )
        inline_retry_count = int(job.retry_count or 0)
        last_error = None
        for attempt in range(inline_retry_count, MAX_PROCESSING_JOB_ATTEMPTS):
            try:
                process_submission_job(str(job.id), retry_count=attempt, task_id="")
                last_error = None
                break
            except Exception as inline_exc:
                last_error = inline_exc
                if attempt + 1 >= MAX_PROCESSING_JOB_ATTEMPTS:
                    break
        if last_error is not None:
            raise last_error
        job.refresh_from_db()

    return job

