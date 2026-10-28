from .job_lifecycle import JOB_CANCEL_MESSAGE, REQUEST_DELETE_MESSAGE


def finalize_cancelled_job(job, message=JOB_CANCEL_MESSAGE):
    from .job_lifecycle import (
        JobStatus,
        JobType,
        SubmissionStatus,
        record_job_log,
        reprocess_target_book_for_job,
        timezone,
    )
    from .retry_and_deduplication import sync_deduplicated_submissions

    submission = job.submission
    submission.status = SubmissionStatus.CANCELLED
    submission.error_message = message
    submission.save(update_fields=["status", "error_message", "updated_at"])
    sync_deduplicated_submissions(submission)

    if job.job_type == JobType.REPROCESS:
        reprocess_book = reprocess_target_book_for_job(job)
        previous_book_state = job.payload.get("previous_book_state")
        if reprocess_book is not None and previous_book_state:
            reprocess_book.state = previous_book_state
            reprocess_book.save(update_fields=["state", "updated_at"])

    job.status = JobStatus.CANCELLED
    job.cancel_requested = False
    job.last_error = message
    job.finished_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "cancel_requested",
            "last_error",
            "finished_at",
            "updated_at",
        ]
    )
    record_job_log(job, "warning", message)
    return job


def cancel_processing_job(job, message=JOB_CANCEL_MESSAGE):
    from .job_lifecycle import (
        JobStatus,
        ProcessingJob,
        record_job_log,
        revoke_processing_task,
    )

    job = ProcessingJob.objects.select_related("submission").get(pk=job.pk)
    if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
        return job

    job.cancel_requested = True
    job.save(update_fields=["cancel_requested", "updated_at"])
    if job.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
        revoke_processing_task(
            job.task_id, terminate=job.status == JobStatus.PROCESSING
        )
        return finalize_cancelled_job(job, message=message)
    record_job_log(job, "warning", "Stop requested.")
    return job


def resume_processing_job(job):
    from .job_lifecycle import (
        JobStatus,
        ProcessingJob,
        SubmissionStatus,
    )
    from .resolution_and_queueing import dispatch_processing_job
    from .retry_and_deduplication import sync_deduplicated_submissions

    job = ProcessingJob.objects.select_related("submission").get(pk=job.pk)
    if job.status not in {JobStatus.QUEUED, JobStatus.CANCELLED}:
        raise ValueError("Only queued or stopped jobs can be resumed.")
    if job.status == JobStatus.CANCELLED:
        job.status = JobStatus.QUEUED
        job.cancel_requested = False
        job.task_id = ""
        job.queue_name = ""
        job.last_error = ""
        job.started_at = None
        job.finished_at = None
        job.save(
            update_fields=[
                "status",
                "cancel_requested",
                "task_id",
                "queue_name",
                "last_error",
                "started_at",
                "finished_at",
                "updated_at",
            ]
        )
        if job.submission.status == SubmissionStatus.CANCELLED:
            job.submission.status = SubmissionStatus.QUEUED
            job.submission.error_message = ""
            job.submission.save(update_fields=["status", "error_message", "updated_at"])
            sync_deduplicated_submissions(job.submission)
    if job.cancel_requested:
        raise ValueError("This job has a pending stop request.")
    dispatch_processing_job(job, force=True)
    return job


def soft_delete_submission_record(submission, message=REQUEST_DELETE_MESSAGE):
    from .job_lifecycle import (
        ACTIVE_JOB_STATUSES,
        JobStatus,
        SubmissionStatus,
        root_submission,
    )
    from .retry_and_deduplication import sync_deduplicated_submissions

    target_submission = root_submission(submission)
    active_jobs = list(
        target_submission.processing_jobs.filter(
            status__in=ACTIVE_JOB_STATUSES,
        ).order_by("-created_at")
    )
    if any(job.status == JobStatus.PROCESSING for job in active_jobs):
        raise ValueError("Stop processing before deleting this request.")
    for job in active_jobs:
        cancel_processing_job(job, message=message)

    update_fields = []
    if target_submission.status != SubmissionStatus.DELETED:
        target_submission.status = SubmissionStatus.DELETED
        update_fields.append("status")
    if target_submission.error_message:
        target_submission.error_message = ""
        update_fields.append("error_message")
    if update_fields:
        target_submission.save(
            update_fields=[*dict.fromkeys(update_fields), "updated_at"]
        )
        sync_deduplicated_submissions(target_submission)
    return target_submission
