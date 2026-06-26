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
    inspect_source_catalog_entry as support_inspect_source_catalog_entry,
    iter_source_catalog_entry_inspections,
    serialize_source_catalog_entry_inspection as support_serialize_source_catalog_entry_inspection,
    should_create_missing_book,
    should_retry_failed_entry,
    should_update_existing_book,
    source_catalog_book_source_map as support_source_catalog_book_source_map,
    source_catalog_entry_snapshots as support_source_catalog_entry_snapshots,
    source_catalog_entry_overview as support_source_catalog_entry_overview,
    source_catalog_submission_map as support_source_catalog_submission_map,
    submission_origin_for_run,
    summarize_source_catalog_snapshots as support_summarize_source_catalog_snapshots,
)
from apps.ingestion.services.curation_support.schedule import (
    next_catalog_automation_due_at as support_next_catalog_automation_due_at,
    normalize_refresh_max_pages as support_normalize_refresh_max_pages,
)
from apps.ingestion.services.curation_support.run_lifecycle import (
    dispatch_catalog_curation_run as support_dispatch_catalog_curation_run,
    finalize_cancelled_catalog_curation_run as support_finalize_cancelled_catalog_curation_run,
    revoke_curation_task as support_revoke_curation_task,
)
from apps.ingestion.services.curation_support.source_refresh import (
    finalize_source_catalog_refresh_stop as support_finalize_source_catalog_refresh_stop,
    get_source_catalog_refresh_state as support_get_source_catalog_refresh_state,
    process_source_catalog_refresh as support_process_source_catalog_refresh,
    revoke_source_catalog_refresh_task as support_revoke_source_catalog_refresh_task,
)
from apps.ingestion.services.resolution import TitleResolver
from apps.ingestion.services.submissions import create_submission_records, queue_reprocess_book
from apps.processing.services import refresh_catalog_parallel

logger = logging.getLogger(__name__)

ACTIVE_RUN_STATUSES = (JobStatus.QUEUED, JobStatus.PROCESSING)
ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES = (SourceCatalogRefreshStatus.QUEUED, SourceCatalogRefreshStatus.PROCESSING)
RUN_CANCEL_MESSAGE = "Stopped by user."
SOURCE_REFRESH_STOP_MESSAGE = "Stopped by user."


def normalize_refresh_max_pages(value): return support_normalize_refresh_max_pages(value)


def get_catalog_automation_settings():
    settings_obj, _ = CatalogAutomationSettings.objects.get_or_create(singleton_key="default")
    return settings_obj


def get_source_catalog_refresh_state(): return support_get_source_catalog_refresh_state()


def latest_catalog_automation_run(): return CatalogCurationRun.objects.filter(trigger=CatalogCurationTrigger.SCHEDULED).order_by("-created_at").first()


def dispatch_source_catalog_refresh(state, force=False):
    from apps.ingestion.tasks import refresh_source_catalog_task

    state.refresh_from_db(fields=["status", "task_id", "queue_name", "updated_at"])
    if not force and state.status == SourceCatalogRefreshStatus.QUEUED and state.task_id:
        return state

    assigned_task_id = str(uuid4())
    state.task_id = assigned_task_id
    state.queue_name = "celery"
    state.save(update_fields=["task_id", "queue_name", "updated_at"])

    try:
        async_result = refresh_source_catalog_task.apply_async(task_id=assigned_task_id)
        dispatched_task_id = getattr(async_result, "id", assigned_task_id) or assigned_task_id
        if dispatched_task_id != assigned_task_id:
            state.task_id = dispatched_task_id
            state.save(update_fields=["task_id", "updated_at"])
    except Exception as exc:
        state.refresh_from_db()
        if settings.CELERY_TASK_ALWAYS_EAGER:
            logger.warning("Source catalog refresh eager execution raised during dispatch.", exc_info=True)
            return state
        logger.warning("Source catalog refresh dispatch failed, falling back to inline processing", exc_info=True)
        state.task_id = ""
        state.queue_name = "inline-fallback"
        state.last_error = f"Celery dispatch failed: {exc}"
        state.save(update_fields=["task_id", "queue_name", "last_error", "updated_at"])
        process_source_catalog_refresh(retry_count=state.retry_count, task_id="")

    return state


def revoke_source_catalog_refresh_task(task_id, terminate=False): return support_revoke_source_catalog_refresh_task(task_id, terminate=terminate)


def finalize_source_catalog_refresh_stop(state, message=SOURCE_REFRESH_STOP_MESSAGE): return support_finalize_source_catalog_refresh_stop(state, message)


def cancel_source_catalog_refresh(state=None, message=SOURCE_REFRESH_STOP_MESSAGE):
    state = state or get_source_catalog_refresh_state()
    state.refresh_from_db(fields=["status", "task_id", "queue_name", "retry_count", "updated_at"])
    if state.status not in ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES:
        return state

    revoke_source_catalog_refresh_task(state.task_id, terminate=state.status == SourceCatalogRefreshStatus.PROCESSING)
    return finalize_source_catalog_refresh_stop(state, message=message)


def begin_source_catalog_refresh(*, requested_by=None, max_pages=None):
    state = get_source_catalog_refresh_state()
    if state.status in ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES:
        return state, False

    state.status = SourceCatalogRefreshStatus.QUEUED
    state.max_pages = normalize_refresh_max_pages(max_pages)
    state.task_id = ""
    state.queue_name = ""
    state.retry_count = 0
    state.refreshed_entries = 0
    state.last_error = ""
    state.requested_by = requested_by if getattr(requested_by, "is_authenticated", False) else None
    state.started_at = None
    state.finished_at = None
    state.save(update_fields=["status", "max_pages", "task_id", "queue_name", "retry_count", "refreshed_entries", "last_error", "requested_by", "started_at", "finished_at", "updated_at"])
    dispatch_source_catalog_refresh(state)
    return state, True


def process_source_catalog_refresh(retry_count=0, task_id=""): return support_process_source_catalog_refresh(retry_count=retry_count, task_id=task_id)


def next_catalog_automation_due_at(settings_obj, now=None, latest_run=None):
    return support_next_catalog_automation_due_at(
        settings_obj,
        now=now,
        latest_run=latest_run or latest_catalog_automation_run(),
    )


def next_catalog_automation_run_at(settings_obj, now=None, latest_run=None): return next_catalog_automation_due_at(settings_obj, now=now, latest_run=latest_run)


def inspect_source_catalog_entry(entry, source_map, submission_map=None): return support_inspect_source_catalog_entry(entry, source_map, submission_map)


def serialize_source_catalog_entry_inspection(inspection): return support_serialize_source_catalog_entry_inspection(inspection)


def summarize_source_catalog_snapshots(snapshots): return support_summarize_source_catalog_snapshots(snapshots)


def source_catalog_book_source_map(source_urls): return support_source_catalog_book_source_map(source_urls)


def source_catalog_submission_map(source_urls): return support_source_catalog_submission_map(source_urls)


def source_catalog_entry_snapshots(queryset): return support_source_catalog_entry_snapshots(queryset)


def source_catalog_entry_overview(queryset, entry_statuses=None):
    return support_source_catalog_entry_overview(
        queryset,
        entry_statuses=entry_statuses,
    )


def revoke_curation_task(task_id): return support_revoke_curation_task(task_id, logger)


def finalize_cancelled_catalog_curation_run(run, message=RUN_CANCEL_MESSAGE): return support_finalize_cancelled_catalog_curation_run(run, message)


def cancel_catalog_curation_run(run, message=RUN_CANCEL_MESSAGE):
    run = CatalogCurationRun.objects.get(pk=run.pk)
    if run.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
        return run

    run.cancel_requested = True
    run.save(update_fields=["cancel_requested", "updated_at"])
    if run.status == JobStatus.QUEUED:
        revoke_curation_task(run.task_id)
        return finalize_cancelled_catalog_curation_run(run, message=message)
    return run


def dispatch_catalog_curation_run(run, force=False):
    return support_dispatch_catalog_curation_run(
        run,
        fallback_processor=process_catalog_curation_run,
        logger=logger,
        force=force,
    )


def create_catalog_curation_run(
    *,
    mode=CatalogCurationMode.PENDING,
    trigger=CatalogCurationTrigger.MANUAL,
    requested_by=None,
    refresh_catalog=True,
    refresh_max_pages=None,
):
    run = CatalogCurationRun.objects.create(
        trigger=trigger,
        mode=mode,
        status=JobStatus.QUEUED,
        requested_by=requested_by if getattr(requested_by, "is_authenticated", False) else None,
        refresh_catalog=refresh_catalog,
        refresh_max_pages=normalize_refresh_max_pages(refresh_max_pages) or 0,
    )
    dispatch_catalog_curation_run(run)
    return run
