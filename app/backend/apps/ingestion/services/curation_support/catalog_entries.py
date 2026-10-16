"""Compatibility exports backed by regular Python modules."""

from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from apps.catalog.models import BookSource, GeneratedAssetStatus, GeneratedAssetType
from apps.common.models import LifecycleState
from apps.ingestion.models import (
    BookSubmission,
    CatalogCurationMode,
    CatalogCurationTrigger,
    JobStatus,
    ProcessingJob,
    SubmissionOrigin,
)

from .catalog_entry_modules.entry_inspection_queries import (
    FAILED_AUTOMATION_RETRY_COOLDOWN,
    HEAVY_BOOK_LIST_FIELDS,
    OVERVIEW_CURATION_STATUSES,
    REQUIRED_READY_ASSETS,
    SOURCE_LOOKUP_CHUNK_SIZE,
    book_has_required_assets,
    inspect_source_catalog_entry,
    inspect_source_catalog_entry_batch,
    iter_source_catalog_entry_inspections,
    iter_source_url_chunks,
    latest_activity_at,
    latest_processing_job_for_submission,
    related_book_list_defer_fields,
    root_submission,
    serialize_source_catalog_entry_inspection,
    source_catalog_book_source_map,
    source_catalog_submission_map,
)
from .catalog_entry_modules.snapshot_summaries import (
    build_catalog_curation_run_summary,
    empty_source_catalog_snapshot_summary,
    should_create_missing_book,
    should_retry_failed_entry,
    should_update_existing_book,
    source_catalog_entry_overview,
    source_catalog_entry_snapshots,
    submission_origin_for_run,
    summarize_source_catalog_snapshots,
    update_source_catalog_snapshot_summary,
)

__all__ = [
    "FAILED_AUTOMATION_RETRY_COOLDOWN",
    "HEAVY_BOOK_LIST_FIELDS",
    "OVERVIEW_CURATION_STATUSES",
    "REQUIRED_READY_ASSETS",
    "SOURCE_LOOKUP_CHUNK_SIZE",
    "BookSource",
    "BookSubmission",
    "CatalogCurationMode",
    "CatalogCurationTrigger",
    "GeneratedAssetStatus",
    "GeneratedAssetType",
    "JobStatus",
    "LifecycleState",
    "Prefetch",
    "ProcessingJob",
    "SubmissionOrigin",
    "book_has_required_assets",
    "build_catalog_curation_run_summary",
    "empty_source_catalog_snapshot_summary",
    "inspect_source_catalog_entry",
    "inspect_source_catalog_entry_batch",
    "iter_source_catalog_entry_inspections",
    "iter_source_url_chunks",
    "latest_activity_at",
    "latest_processing_job_for_submission",
    "related_book_list_defer_fields",
    "root_submission",
    "serialize_source_catalog_entry_inspection",
    "should_create_missing_book",
    "should_retry_failed_entry",
    "should_update_existing_book",
    "source_catalog_book_source_map",
    "source_catalog_entry_overview",
    "source_catalog_entry_snapshots",
    "source_catalog_submission_map",
    "submission_origin_for_run",
    "summarize_source_catalog_snapshots",
    "timedelta",
    "timezone",
    "update_source_catalog_snapshot_summary",
]
