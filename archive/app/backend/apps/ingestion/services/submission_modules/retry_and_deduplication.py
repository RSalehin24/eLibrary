

def delete_submission_record(submission):
    target_submission = root_submission(submission)
    if target_submission.status == SubmissionStatus.DELETED:
        target_submission.delete()
        return "hard_deleted"
    soft_delete_submission_record(target_submission)
    return "soft_deleted"


def fail_processing_job(job, message):
    submission = job.submission
    submission.status = SubmissionStatus.FAILED
    submission.error_message = message
    submission.save(update_fields=["status", "error_message", "updated_at"])
    sync_deduplicated_submissions(submission)

    job.status = JobStatus.FAILED
    job.cancel_requested = False
    job.task_id = ""
    job.queue_name = ""
    job.last_error = message
    job.finished_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "cancel_requested",
            "task_id",
            "queue_name",
            "last_error",
            "finished_at",
            "updated_at",
        ]
    )
    record_job_log(job, "error", message, {"auto_failed": True})
    return job


def requeue_processing_job(
    job,
    *,
    retry_count=0,
    message="",
    preserve_dispatch_state=False,
):
    submission = job.submission
    submission.status = SubmissionStatus.QUEUED
    submission.error_message = ""
    submission.save(update_fields=["status", "error_message", "updated_at"])
    sync_deduplicated_submissions(submission)

    job.status = JobStatus.QUEUED
    job.retry_count = retry_count
    job.cancel_requested = False
    if not preserve_dispatch_state:
        job.task_id = ""
        job.queue_name = ""
    job.last_error = message
    job.started_at = None
    job.finished_at = None
    update_fields = [
        "status",
        "retry_count",
        "cancel_requested",
        "last_error",
        "started_at",
        "finished_at",
        "updated_at",
    ]
    if not preserve_dispatch_state:
        update_fields.extend(["task_id", "queue_name"])
    job.save(update_fields=update_fields)
    record_job_log(
        job,
        "warning",
        message or "Processing job was requeued automatically.",
        {
            "auto_requeued": True,
            "retry_count": retry_count,
            "preserve_dispatch_state": preserve_dispatch_state,
        },
    )
    return job


def recover_stale_processing_jobs(
    *,
    origin="",
    limit=50,
    stale_after=STALE_PROCESSING_JOB_AFTER,
):
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
                | (
                    Q(started_at__isnull=True)
                    & Q(updated_at__lt=stale_before)
                )
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


def capture_source_page_metadata(source_url):
    try:
        metadata = fetch_source_page_metadata(source_url)
    except Exception:
        return None

    upsert_source_catalog_entry(metadata)
    return metadata


def retry_submission_record(submission, actor):
    target_submission = root_submission(submission)
    can_manage_processing = can_manage_processing_records(actor)
    if not actor.is_staff and not can_manage_processing and submission.submitter_id != actor.id:
        raise PermissionDenied("You cannot retry this submission.")
    if not target_submission.resolved_url and target_submission.input_type != "title":
        raise ValueError("This submission does not have a resolved URL yet.")

    previous_status = target_submission.status
    previous_error_message = (target_submission.error_message or "").strip()
    update_fields = []

    if target_submission.linked_book_id and target_submission.linked_book and target_submission.linked_book.deleted_at:
        target_submission.linked_book = None
        update_fields.append("linked_book")
    if target_submission.duplicate_of_book_id and (
        not target_submission.duplicate_of_book or target_submission.duplicate_of_book.deleted_at
    ):
        target_submission.duplicate_of_book = None
        update_fields.append("duplicate_of_book")
    if target_submission.error_message:
        target_submission.error_message = ""
        update_fields.append("error_message")

    next_payload = build_retry_payload(
        target_submission.raw_payload,
        actor,
        previous_status,
        previous_error_message,
        RETRY_PAYLOAD_RESET_KEYS,
    )
    if next_payload != (target_submission.raw_payload or {}):
        target_submission.raw_payload = next_payload
        update_fields.append("raw_payload")

    if target_submission.review_state != ReviewState.PENDING:
        target_submission.review_state = ReviewState.PENDING
        update_fields.append("review_state")
    if target_submission.status not in {SubmissionStatus.QUEUED, SubmissionStatus.PROCESSING}:
        target_submission.status = SubmissionStatus.QUEUED
        update_fields.append("status")

    if update_fields:
        target_submission.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
        sync_deduplicated_submissions(target_submission)

    return queue_submission(target_submission, actor=actor)


def retry_submission_records(submissions, actor):
    queued_count = 0
    skipped_invalid = 0
    skipped_duplicate_targets = 0
    seen_target_ids = set()

    for submission in submissions:
        target_id = str(submission.canonical_submission_id or submission.id)
        if target_id in seen_target_ids:
            skipped_duplicate_targets += 1
            continue
        seen_target_ids.add(target_id)

        try:
            retry_submission_record(submission, actor)
        except ValueError:
            skipped_invalid += 1
            continue

        queued_count += 1

    return {
        "queued_count": queued_count,
        "skipped_invalid": skipped_invalid,
        "skipped_duplicate_targets": skipped_duplicate_targets,
    }


def sync_submission_from_canonical(submission, canonical_submission):
    return _sync_submission_from_canonical(
        submission,
        canonical_submission,
        ensure_preview_session_callback=ensure_preview_session,
        root_submission_callback=root_submission,
        shared_payload_keys=SUBMISSION_PAYLOAD_KEYS_TO_SHARE,
        submission_status=SubmissionStatus,
    )


def sync_deduplicated_submissions(submission):
    return _sync_deduplicated_submissions(
        submission,
        root_submission_callback=root_submission,
        sync_submission_from_canonical_callback=sync_submission_from_canonical,
    )
