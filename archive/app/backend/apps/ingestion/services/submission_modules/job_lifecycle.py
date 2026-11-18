import logging
from datetime import timedelta
from uuid import uuid4

from celery import current_app
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    Contributor,
    GeneratedAssetType,
    Series,
    ContributorRole,
    CuratedDocumentStatus,
)
from apps.catalog.services import (
    find_deleted_book_by_title,
    find_existing_book_by_source_url,
    replace_book_relations,
)
from apps.common.models import AuditLog, LifecycleState, ReviewState
from apps.common.text import normalize_catalog_text
from apps.ingestion.models import (
    BookSubmission,
    DuplicateReview,
    DuplicateReviewStatus,
    JobStatus,
    JobType,
    MatchCandidate,
    ProcessingJob,
    ProcessingLog,
    ResolutionStatus,
    SubmissionOrigin,
    SubmissionInputType,
    SubmissionStatus,
    TitleResolutionAttempt,
)
from apps.ingestion.services.legacy_adapter import (
    generate_exports,
    high_fidelity_scrape_limits,
    load_legacy_config_entries,
    normalize_source_url,
    normalize_text,
    scrape_book,
    scrape_book_high_fidelity,
    texts_are_similar,
    validate_source_url,
)
from apps.ingestion.pipeline.curated_pipeline import curate_scraped_book_data
from apps.ingestion.pipeline.curated_pipeline import curate_book_document
from apps.ingestion.pipeline.curated_export import curated_document_with_projection
from apps.ingestion.pipeline.curated_persistence import (
    persist_curated_book_with_hooks as _persist_curated_book,
    persist_curated_document,
)
from apps.ingestion.services.normalization import clean_extracted_dedication_html, normalize_scraped_book, promote_leading_front_matter
from apps.ingestion.services.resolution import (
    TitleResolver,
    fetch_source_page_metadata,
    upsert_source_catalog_entry,
)
from apps.ingestion.services.submissions_support.assets import (
    calculate_checksum,
    candidate_asset_paths,
    cleanup_staged_asset_files,
    content_type_for_suffix,
    path_is_within,
    resolve_generated_cover_path,
    sync_assets as _sync_assets,
)
from apps.ingestion.services.submissions_support.detection import (
    detect_metadata_duplicate as _detect_metadata_duplicate,
    find_exact_existing_book as _find_exact_existing_book,
)
from apps.ingestion.services.submissions_support.persistence import (
    complete_processed_submission as _complete_processed_submission,
    export_payload_from_book,
    persist_scraped_book as _persist_scraped_book,
    sync_metadata_relations as _sync_metadata_relations,
)
from apps.ingestion.services.submissions_support.preview import (
    can_manage_processing_records,
    ensure_preview_session,
)
from apps.ingestion.services.submissions_support.sync import (
    build_retry_payload,
    primary_source_url_for_book,
    root_submission,
    sync_deduplicated_submissions as _sync_deduplicated_submissions,
    sync_submission_from_canonical as _sync_submission_from_canonical,
)

logger = logging.getLogger(__name__)

REUSABLE_SUBMISSION_STATUSES = (
    SubmissionStatus.PENDING_RESOLUTION,
    SubmissionStatus.QUEUED,
    SubmissionStatus.PROCESSING,
    SubmissionStatus.READY,
)

SUBMISSION_PAYLOAD_KEYS_TO_SHARE = (
    "served_from_database",
    "existing_book_source",
    "linked_book_slug",
    "source_page_metadata",
    "normalized_url",
    "scraped_preview",
)

ACTIVE_JOB_STATUSES = (JobStatus.QUEUED, JobStatus.PROCESSING)
JOB_CANCEL_MESSAGE = "Stopped by user."
REQUEST_DELETE_MESSAGE = "Deleted by user."
REQUIRED_GENERATED_ASSET_TYPES = (GeneratedAssetType.HTML, GeneratedAssetType.EPUB)
GENERATED_ASSET_LABELS = {
    GeneratedAssetType.HTML: "HTML",
    GeneratedAssetType.EPUB: "EPUB",
}
MAX_PROCESSING_JOB_ATTEMPTS = 3
STALE_PROCESSING_JOB_AFTER = timedelta(minutes=20)
STALE_PROCESSING_RETRY_MESSAGE = (
    "Processing exceeded the recovery window and was retried automatically."
)
STALE_PROCESSING_FAILURE_MESSAGE = (
    "Processing exceeded the recovery window and failed after the maximum retry attempts."
)
PROCESSING_RETRY_MESSAGE_TEMPLATE = (
    "Processing failed on attempt {attempt} of {max_attempts} and will retry automatically."
)
RETRY_PAYLOAD_RESET_KEYS = (
    "served_from_database",
    "existing_book_source",
    "linked_book_slug",
)


def record_job_log(job, level, message, details=None):
    return ProcessingLog.objects.create(
        job=job,
        level=level,
        message=message,
        details=details or {},
    )


def revoke_processing_task(task_id, *, terminate=False):
    if not task_id:
        return
    try:
        current_app.control.revoke(task_id, terminate=terminate)
    except Exception:
        logger.warning("Failed to revoke processing task.", exc_info=True)


def reprocess_target_book_for_job(job):
    reprocess_book_id = job.payload.get("reprocess_book_id") or job.book_id or job.submission.linked_book_id
    if not reprocess_book_id:
        return None
    return Book.objects.filter(pk=reprocess_book_id).first()


def finalize_cancelled_job(job, message=JOB_CANCEL_MESSAGE):
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
    job.save(update_fields=["status", "cancel_requested", "last_error", "finished_at", "updated_at"])
    record_job_log(job, "warning", message)
    return job


def cancel_processing_job(job, message=JOB_CANCEL_MESSAGE):
    job = ProcessingJob.objects.select_related("submission").get(pk=job.pk)
    if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
        return job

    job.cancel_requested = True
    job.save(update_fields=["cancel_requested", "updated_at"])
    if job.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
        revoke_processing_task(job.task_id, terminate=job.status == JobStatus.PROCESSING)
        return finalize_cancelled_job(job, message=message)
    record_job_log(job, "warning", "Stop requested.")
    return job


def resume_processing_job(job):
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
        target_submission.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
        sync_deduplicated_submissions(target_submission)
    return target_submission
