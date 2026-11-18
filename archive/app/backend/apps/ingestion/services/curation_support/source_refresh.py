import logging

from celery import current_app
from django.utils import timezone

from apps.ingestion.models import SourceCatalogRefreshState, SourceCatalogRefreshStatus
from apps.processing.services import refresh_catalog_parallel


logger = logging.getLogger(__name__)


def get_source_catalog_refresh_state():
    state, _ = SourceCatalogRefreshState.objects.get_or_create(singleton_key="default")
    return state


def revoke_source_catalog_refresh_task(task_id, terminate=False):
    if not task_id:
        return
    try:
        current_app.control.revoke(task_id, terminate=terminate)
    except Exception:
        logger.warning("Failed to revoke source catalog refresh task.", exc_info=True)


def finalize_source_catalog_refresh_stop(state, message):
    state.status = SourceCatalogRefreshStatus.IDLE
    state.task_id = ""
    state.queue_name = ""
    state.retry_count = 0
    state.last_error = message
    state.finished_at = timezone.now()
    state.save(update_fields=["status", "task_id", "queue_name", "retry_count", "last_error", "finished_at", "updated_at"])
    return state


def refresh_state_can_finalize(task_id):
    state = SourceCatalogRefreshState.objects.get(singleton_key="default")
    current_task_id = (state.task_id or "").strip()
    incoming_task_id = (task_id or "").strip()
    active_statuses = {
        SourceCatalogRefreshStatus.QUEUED,
        SourceCatalogRefreshStatus.PROCESSING,
    }

    if incoming_task_id and current_task_id != incoming_task_id:
        return False, state
    if state.status not in active_statuses:
        return False, state
    return True, state


def process_source_catalog_refresh(retry_count=0, task_id=""):
    state = SourceCatalogRefreshState.objects.select_related("requested_by").get(singleton_key="default")
    active_statuses = {
        SourceCatalogRefreshStatus.QUEUED,
        SourceCatalogRefreshStatus.PROCESSING,
    }
    current_task_id = (state.task_id or "").strip()
    incoming_task_id = (task_id or "").strip()

    # Ignore stale tasks that start after the refresh was stopped or replaced.
    if incoming_task_id:
        if current_task_id and current_task_id != incoming_task_id:
            logger.info(
                "Skipping stale source catalog refresh task.",
                extra={
                    "current_task_id": current_task_id,
                    "incoming_task_id": incoming_task_id,
                    "status": state.status,
                },
            )
            return state
        if not current_task_id and state.status not in active_statuses:
            logger.info(
                "Skipping inactive source catalog refresh task.",
                extra={
                    "incoming_task_id": incoming_task_id,
                    "status": state.status,
                },
            )
            return state

    state.status = SourceCatalogRefreshStatus.PROCESSING
    state.retry_count = retry_count
    state.task_id = task_id or state.task_id
    state.started_at = timezone.now()
    state.finished_at = None
    state.last_error = ""
    state.save(update_fields=["status", "retry_count", "task_id", "started_at", "finished_at", "last_error", "updated_at"])

    try:
        result = refresh_catalog_parallel()
        can_finalize, state = refresh_state_can_finalize(task_id)
        if not can_finalize:
            logger.info(
                "Skipping completed source catalog refresh task that no longer owns the refresh state.",
                extra={
                    "incoming_task_id": incoming_task_id,
                    "current_task_id": (state.task_id or "").strip(),
                    "status": state.status,
                },
            )
            return state
        state.status = SourceCatalogRefreshStatus.SUCCEEDED
        state.refreshed_entries = result["total"]
        state.finished_at = timezone.now()
        state.save(update_fields=["status", "refreshed_entries", "finished_at", "updated_at"])
        return state
    except Exception as exc:
        logger.exception("Source catalog refresh failed")
        can_finalize, state = refresh_state_can_finalize(task_id)
        if not can_finalize:
            logger.info(
                "Skipping failed source catalog refresh task that no longer owns the refresh state.",
                extra={
                    "incoming_task_id": incoming_task_id,
                    "current_task_id": (state.task_id or "").strip(),
                    "status": state.status,
                },
            )
            return state
        state.status = SourceCatalogRefreshStatus.FAILED
        state.last_error = str(exc)
        state.finished_at = timezone.now()
        state.save(update_fields=["status", "last_error", "finished_at", "updated_at"])
        raise
