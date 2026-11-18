from uuid import uuid4

from celery import current_app
from django.conf import settings
from django.utils import timezone

from apps.ingestion.models import JobStatus


def revoke_curation_task(task_id, logger):
    if not task_id:
        return
    try:
        current_app.control.revoke(task_id)
    except Exception:
        logger.warning("Failed to revoke catalog curation task.", exc_info=True)


def finalize_cancelled_catalog_curation_run(run, message):
    run.status = JobStatus.CANCELLED
    run.cancel_requested = False
    run.last_error = message
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "cancel_requested", "last_error", "finished_at", "updated_at"])
    return run


def dispatch_catalog_curation_run(run, *, fallback_processor, logger, force=False):
    from apps.ingestion.tasks import process_catalog_curation_run_task

    run.refresh_from_db(fields=["status", "task_id", "queue_name", "cancel_requested", "updated_at"])
    if run.status == JobStatus.CANCELLED or run.cancel_requested:
        return run
    if not force and run.status == JobStatus.QUEUED and run.task_id:
        return run

    assigned_task_id = str(uuid4())
    run.task_id = assigned_task_id
    run.queue_name = "celery"
    run.save(update_fields=["task_id", "queue_name", "updated_at"])

    try:
        async_result = process_catalog_curation_run_task.apply_async(
            args=[str(run.id)],
            task_id=assigned_task_id,
        )
        dispatched_task_id = getattr(async_result, "id", assigned_task_id) or assigned_task_id
        if dispatched_task_id != assigned_task_id:
            run.task_id = dispatched_task_id
            run.save(update_fields=["task_id", "updated_at"])
    except Exception as exc:
        run.refresh_from_db()
        if settings.CELERY_TASK_ALWAYS_EAGER:
            logger.warning("Catalog curation eager execution raised during dispatch.", exc_info=True)
            return run
        logger.warning("Catalog curation dispatch failed, falling back to inline processing", exc_info=True)
        run.task_id = ""
        run.queue_name = "inline-fallback"
        run.last_error = f"Celery dispatch failed: {exc}"
        run.save(update_fields=["task_id", "queue_name", "last_error", "updated_at"])
        fallback_processor(str(run.id), retry_count=run.retry_count, task_id="")

    return run
