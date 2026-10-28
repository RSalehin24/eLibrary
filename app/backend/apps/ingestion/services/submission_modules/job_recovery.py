from .job_lifecycle import STALE_PROCESSING_JOB_AFTER
from .retry_and_deduplication import fail_processing_job, requeue_processing_job


def recover_stale_processing_jobs(
    *,
    origin="",
    limit=50,
    stale_after=STALE_PROCESSING_JOB_AFTER,
):
    from .job_lifecycle import (
        MAX_PROCESSING_JOB_ATTEMPTS,
        STALE_PROCESSING_FAILURE_MESSAGE,
        STALE_PROCESSING_RETRY_MESSAGE,
        JobStatus,
        ProcessingJob,
        Q,
        revoke_processing_task,
        timezone,
    )
    from .resolution_and_queueing import dispatch_processing_job

    queryset = ProcessingJob.objects.select_related("submission").filter(
        cancel_requested=False
    )
    if origin:
        queryset = queryset.filter(submission__origin=origin)

    queued_job_ids = list(
        queryset.filter(status=JobStatus.QUEUED)
        .filter(Q(task_id="") | Q(task_id__isnull=True))
        .order_by("created_at")
        .values_list("id", flat=True)[:limit]
    )
    remaining_limit = max(limit - len(queued_job_ids), 0)
    stale_before = timezone.now() - stale_after
    stale_job_ids = []
    if remaining_limit:
        stale_job_ids = list(
            queryset.filter(status=JobStatus.PROCESSING)
            .filter(
                Q(started_at__lt=stale_before)
                | (Q(started_at__isnull=True) & Q(updated_at__lt=stale_before))
            )
            .order_by("created_at")
            .values_list("id", flat=True)[:remaining_limit]
        )

    recovered = 0
    jobs = list(
        ProcessingJob.objects.select_related("submission")
        .filter(pk__in=[*queued_job_ids, *stale_job_ids])
        .order_by("created_at")
    )

    for job in jobs:
        if job.status == JobStatus.PROCESSING:
            revoke_processing_task(job.task_id, terminate=True)
            next_retry_count = int(job.retry_count or 0) + 1
            if next_retry_count >= MAX_PROCESSING_JOB_ATTEMPTS:
                fail_processing_job(job, STALE_PROCESSING_FAILURE_MESSAGE)
                continue
            requeue_processing_job(
                job,
                retry_count=next_retry_count,
                message=STALE_PROCESSING_RETRY_MESSAGE,
            )

        dispatch_processing_job(job, force=True)
        recovered += 1
    return recovered
