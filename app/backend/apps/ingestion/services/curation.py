"""Compatibility exports backed by regular Python modules."""

import logging
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from apps.ingestion.models import (
    CatalogAutomationSettings,
    CatalogCurationMode,
    CatalogCurationRun,
    CatalogCurationTrigger,
    JobStatus,
    SourceCatalogEntry,
    SourceCatalogRefreshStatus,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    build_catalog_curation_run_summary,
    iter_source_catalog_entry_inspections,
    should_create_missing_book,
    should_retry_failed_entry,
    should_update_existing_book,
    submission_origin_for_run,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    inspect_source_catalog_entry as support_inspect_source_catalog_entry,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    serialize_source_catalog_entry_inspection as support_serialize_source_catalog_entry_inspection,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    source_catalog_book_source_map as support_source_catalog_book_source_map,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    source_catalog_entry_overview as support_source_catalog_entry_overview,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    source_catalog_entry_snapshots as support_source_catalog_entry_snapshots,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    source_catalog_submission_map as support_source_catalog_submission_map,
)
from apps.ingestion.services.curation_support.catalog_entries import (
    summarize_source_catalog_snapshots as support_summarize_source_catalog_snapshots,
)
from apps.ingestion.services.curation_support.run_lifecycle import (
    dispatch_catalog_curation_run as support_dispatch_catalog_curation_run,
)
from apps.ingestion.services.curation_support.run_lifecycle import (
    finalize_cancelled_catalog_curation_run as support_finalize_cancelled_catalog_curation_run,
)
from apps.ingestion.services.curation_support.run_lifecycle import (
    revoke_curation_task as support_revoke_curation_task,
)
from apps.ingestion.services.curation_support.schedule import (
    next_catalog_automation_due_at as support_next_catalog_automation_due_at,
)
from apps.ingestion.services.curation_support.schedule import (
    normalize_refresh_max_pages as support_normalize_refresh_max_pages,
)
from apps.ingestion.services.curation_support.source_refresh import (
    finalize_source_catalog_refresh_stop as support_finalize_source_catalog_refresh_stop,
)
from apps.ingestion.services.curation_support.source_refresh import (
    get_source_catalog_refresh_state as support_get_source_catalog_refresh_state,
)
from apps.ingestion.services.curation_support.source_refresh import (
    process_source_catalog_refresh as support_process_source_catalog_refresh,
)
from apps.ingestion.services.curation_support.source_refresh import (
    revoke_source_catalog_refresh_task as support_revoke_source_catalog_refresh_task,
)
from apps.ingestion.services.resolution import TitleResolver
from apps.ingestion.services.submissions import (
    create_submission_records,
    queue_reprocess_book,
)
from apps.processing.services import refresh_catalog_parallel

from .curation_modules.catalog_automation_runs import (
    process_catalog_curation_run,
    run_due_catalog_automation,
)
from .curation_modules.source_refresh_and_settings import (
    ACTIVE_RUN_STATUSES,
    ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES,
    RUN_CANCEL_MESSAGE,
    SOURCE_REFRESH_STOP_MESSAGE,
    begin_source_catalog_refresh,
    cancel_catalog_curation_run,
    cancel_source_catalog_refresh,
    create_catalog_curation_run,
    dispatch_catalog_curation_run,
    dispatch_source_catalog_refresh,
    finalize_cancelled_catalog_curation_run,
    finalize_source_catalog_refresh_stop,
    get_catalog_automation_settings,
    get_source_catalog_refresh_state,
    inspect_source_catalog_entry,
    latest_catalog_automation_run,
    logger,
    next_catalog_automation_due_at,
    next_catalog_automation_run_at,
    normalize_refresh_max_pages,
    process_source_catalog_refresh,
    revoke_curation_task,
    revoke_source_catalog_refresh_task,
    serialize_source_catalog_entry_inspection,
    source_catalog_book_source_map,
    source_catalog_entry_overview,
    source_catalog_entry_snapshots,
    source_catalog_submission_map,
    summarize_source_catalog_snapshots,
)

__all__ = [
    "ACTIVE_RUN_STATUSES",
    "ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES",
    "RUN_CANCEL_MESSAGE",
    "SOURCE_REFRESH_STOP_MESSAGE",
    "CatalogAutomationSettings",
    "CatalogCurationMode",
    "CatalogCurationRun",
    "CatalogCurationTrigger",
    "JobStatus",
    "SourceCatalogEntry",
    "SourceCatalogRefreshStatus",
    "TitleResolver",
    "begin_source_catalog_refresh",
    "build_catalog_curation_run_summary",
    "cancel_catalog_curation_run",
    "cancel_source_catalog_refresh",
    "create_catalog_curation_run",
    "create_submission_records",
    "dispatch_catalog_curation_run",
    "dispatch_source_catalog_refresh",
    "finalize_cancelled_catalog_curation_run",
    "finalize_source_catalog_refresh_stop",
    "get_catalog_automation_settings",
    "get_source_catalog_refresh_state",
    "inspect_source_catalog_entry",
    "iter_source_catalog_entry_inspections",
    "latest_catalog_automation_run",
    "logger",
    "logging",
    "next_catalog_automation_due_at",
    "next_catalog_automation_run_at",
    "normalize_refresh_max_pages",
    "process_catalog_curation_run",
    "process_source_catalog_refresh",
    "queue_reprocess_book",
    "refresh_catalog_parallel",
    "revoke_curation_task",
    "revoke_source_catalog_refresh_task",
    "run_due_catalog_automation",
    "serialize_source_catalog_entry_inspection",
    "settings",
    "should_create_missing_book",
    "should_retry_failed_entry",
    "should_update_existing_book",
    "source_catalog_book_source_map",
    "source_catalog_entry_overview",
    "source_catalog_entry_snapshots",
    "source_catalog_submission_map",
    "submission_origin_for_run",
    "summarize_source_catalog_snapshots",
    "support_dispatch_catalog_curation_run",
    "support_finalize_cancelled_catalog_curation_run",
    "support_finalize_source_catalog_refresh_stop",
    "support_get_source_catalog_refresh_state",
    "support_inspect_source_catalog_entry",
    "support_next_catalog_automation_due_at",
    "support_normalize_refresh_max_pages",
    "support_process_source_catalog_refresh",
    "support_revoke_curation_task",
    "support_revoke_source_catalog_refresh_task",
    "support_serialize_source_catalog_entry_inspection",
    "support_source_catalog_book_source_map",
    "support_source_catalog_entry_overview",
    "support_source_catalog_entry_snapshots",
    "support_source_catalog_submission_map",
    "support_summarize_source_catalog_snapshots",
    "timezone",
    "uuid4",
]
