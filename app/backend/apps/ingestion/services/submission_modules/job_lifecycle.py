import logging
from datetime import timedelta
from uuid import uuid4

from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    Contributor,
    ContributorRole,
    CuratedDocumentStatus,
    GeneratedAssetType,
    Series,
)
from apps.catalog.services import (
    find_deleted_book_by_title,
    find_existing_book_by_source_url,
    replace_book_relations,
)
from apps.common.models import AuditLog, LifecycleState
from apps.common.text import normalize_catalog_text
from apps.ingestion.models import (
    BookSubmission,
    JobStatus,
    JobType,
    MatchCandidate,
    ProcessingJob,
    ProcessingLog,
    ResolutionStatus,
    SubmissionInputType,
    SubmissionOrigin,
    SubmissionStatus,
    TitleResolutionAttempt,
)
from apps.ingestion.pipeline.curated_export import curated_document_with_projection
from apps.ingestion.pipeline.curated_persistence import (
    persist_curated_book_with_hooks as _persist_curated_book,
)
from apps.ingestion.pipeline.curated_persistence import (
    persist_curated_document,
)
from apps.ingestion.pipeline.curated_pipeline import (
    curate_book_document,
    curate_scraped_book_data,
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
from apps.ingestion.services.normalization import (
    clean_extracted_dedication_html,
    normalize_scraped_book,
    promote_leading_front_matter,
)
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
)
from apps.ingestion.services.submissions_support.assets import (
    sync_assets as _sync_assets,
)
from apps.ingestion.services.submissions_support.detection import (
    detect_metadata_duplicate as _detect_metadata_duplicate,
)
from apps.ingestion.services.submissions_support.detection import (
    find_exact_existing_book as _find_exact_existing_book,
)
from apps.ingestion.services.submissions_support.persistence import (
    complete_processed_submission as _complete_processed_submission,
)
from apps.ingestion.services.submissions_support.persistence import (
    export_payload_from_book,
)
from apps.ingestion.services.submissions_support.persistence import (
    persist_scraped_book as _persist_scraped_book,
)
from apps.ingestion.services.submissions_support.persistence import (
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
)
from apps.ingestion.services.submissions_support.sync import (
    sync_deduplicated_submissions as _sync_deduplicated_submissions,
)
from apps.ingestion.services.submissions_support.sync import (
    sync_submission_from_canonical as _sync_submission_from_canonical,
)
from celery import current_app
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .job_configuration import (
    ACTIVE_JOB_STATUSES,
    GENERATED_ASSET_LABELS,
    JOB_CANCEL_MESSAGE,
    MAX_PROCESSING_JOB_ATTEMPTS,
    PROCESSING_RETRY_MESSAGE_TEMPLATE,
    REQUEST_DELETE_MESSAGE,
    REQUIRED_GENERATED_ASSET_TYPES,
    RETRY_PAYLOAD_RESET_KEYS,
    REUSABLE_SUBMISSION_STATUSES,
    STALE_PROCESSING_FAILURE_MESSAGE,
    STALE_PROCESSING_JOB_AFTER,
    STALE_PROCESSING_RETRY_MESSAGE,
    SUBMISSION_PAYLOAD_KEYS_TO_SHARE,
)

logger = logging.getLogger(__name__)


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
    reprocess_book_id = (
        job.payload.get("reprocess_book_id")
        or job.book_id
        or job.submission.linked_book_id
    )
    if not reprocess_book_id:
        return None
    return Book.objects.filter(pk=reprocess_book_id).first()


def finalize_cancelled_job(job, message=JOB_CANCEL_MESSAGE):
    from .job_controls import finalize_cancelled_job as run_command

    return run_command(job, message)


def cancel_processing_job(job, message=JOB_CANCEL_MESSAGE):
    from .job_controls import cancel_processing_job as run_command

    return run_command(job, message)


def resume_processing_job(job):
    from .job_controls import resume_processing_job as run_command

    return run_command(job)


def soft_delete_submission_record(submission, message=REQUEST_DELETE_MESSAGE):
    from .job_controls import soft_delete_submission_record as run_command

    return run_command(submission, message)


__all__ = [
    "ACTIVE_JOB_STATUSES",
    "GENERATED_ASSET_LABELS",
    "JOB_CANCEL_MESSAGE",
    "MAX_PROCESSING_JOB_ATTEMPTS",
    "PROCESSING_RETRY_MESSAGE_TEMPLATE",
    "REQUEST_DELETE_MESSAGE",
    "REQUIRED_GENERATED_ASSET_TYPES",
    "RETRY_PAYLOAD_RESET_KEYS",
    "REUSABLE_SUBMISSION_STATUSES",
    "STALE_PROCESSING_FAILURE_MESSAGE",
    "STALE_PROCESSING_JOB_AFTER",
    "STALE_PROCESSING_RETRY_MESSAGE",
    "SUBMISSION_PAYLOAD_KEYS_TO_SHARE",
    "AuditLog",
    "Book",
    "BookCategory",
    "BookContributor",
    "BookSeries",
    "BookSubmission",
    "Category",
    "Contributor",
    "ContributorRole",
    "CuratedDocumentStatus",
    "GeneratedAssetType",
    "IntegrityError",
    "JobStatus",
    "JobType",
    "LifecycleState",
    "MatchCandidate",
    "PermissionDenied",
    "ProcessingJob",
    "ProcessingLog",
    "Q",
    "ResolutionStatus",
    "Series",
    "SubmissionInputType",
    "SubmissionOrigin",
    "SubmissionStatus",
    "TitleResolutionAttempt",
    "TitleResolver",
    "_complete_processed_submission",
    "_detect_metadata_duplicate",
    "_find_exact_existing_book",
    "_persist_curated_book",
    "_persist_scraped_book",
    "_sync_assets",
    "_sync_deduplicated_submissions",
    "_sync_metadata_relations",
    "_sync_submission_from_canonical",
    "build_retry_payload",
    "calculate_checksum",
    "can_manage_processing_records",
    "cancel_processing_job",
    "candidate_asset_paths",
    "clean_extracted_dedication_html",
    "cleanup_staged_asset_files",
    "content_type_for_suffix",
    "curate_book_document",
    "curate_scraped_book_data",
    "curated_document_with_projection",
    "current_app",
    "ensure_preview_session",
    "export_payload_from_book",
    "fetch_source_page_metadata",
    "finalize_cancelled_job",
    "find_deleted_book_by_title",
    "find_existing_book_by_source_url",
    "generate_exports",
    "high_fidelity_scrape_limits",
    "load_legacy_config_entries",
    "logger",
    "logging",
    "normalize_catalog_text",
    "normalize_scraped_book",
    "normalize_source_url",
    "normalize_text",
    "path_is_within",
    "persist_curated_document",
    "primary_source_url_for_book",
    "promote_leading_front_matter",
    "record_job_log",
    "replace_book_relations",
    "reprocess_target_book_for_job",
    "resolve_generated_cover_path",
    "resume_processing_job",
    "revoke_processing_task",
    "root_submission",
    "scrape_book",
    "scrape_book_high_fidelity",
    "settings",
    "soft_delete_submission_record",
    "texts_are_similar",
    "timedelta",
    "timezone",
    "transaction",
    "upsert_source_catalog_entry",
    "uuid4",
    "validate_source_url",
]
