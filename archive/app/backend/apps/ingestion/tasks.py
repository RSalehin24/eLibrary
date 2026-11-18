import logging

from celery import shared_task
from django.db import OperationalError, ProgrammingError

from apps.ingestion.models import ProcessingJob, SubmissionOrigin
from apps.ingestion.services.curation import (
    get_catalog_automation_settings,
    process_catalog_curation_run,
    process_source_catalog_refresh,
    run_due_catalog_automation,
)
from apps.ingestion.services.submissions import (
    MAX_PROCESSING_JOB_ATTEMPTS,
    process_submission_job,
    recover_stale_processing_jobs,
)

logger = logging.getLogger(__name__)

CATALOG_AUTOMATION_SCHEMA_TABLES = (
    "ingestion_catalogautomationsettings",
    "ingestion_catalogcurationrun",
)


def serialize_processing_job_result(result):
    if not isinstance(result, ProcessingJob):
        return result

    return {
        "job_id": str(result.id),
        "submission_id": str(result.submission_id),
        "book_id": str(result.book_id) if result.book_id else "",
        "status": result.status,
    }


def serialize_source_catalog_refresh_result(result):
    if not result:
        return result

    return {
        "id": str(result.id),
        "status": result.status,
        "task_id": result.task_id,
        "queue_name": result.queue_name,
        "retry_count": result.retry_count,
        "refreshed_entries": result.refreshed_entries,
        "last_error": result.last_error,
        "started_at": result.started_at.isoformat() if result.started_at else None,
        "finished_at": result.finished_at.isoformat() if result.finished_at else None,
    }


def catalog_automation_schema_not_ready(exc):
    message = str(exc).lower()
    table_missing = (
        "no such table" in message
        or "undefinedtable" in message
        or ("relation" in message and "does not exist" in message)
    )
    if not table_missing:
        return False
    return any(table_name in message for table_name in CATALOG_AUTOMATION_SCHEMA_TABLES)


@shared_task(
    bind=True,
    retry_backoff=True,
    retry_jitter=True,
    max_retries=MAX_PROCESSING_JOB_ATTEMPTS - 1,
)
def process_submission_task(self, job_id, attempt_offset=0):
    retry_count = max(0, int(attempt_offset or 0)) + int(self.request.retries or 0)
    try:
        result = process_submission_job(
            job_id,
            retry_count=retry_count,
            task_id=self.request.id,
        )
    except Exception as exc:
        if retry_count + 1 >= MAX_PROCESSING_JOB_ATTEMPTS:
            raise
        raise self.retry(exc=exc)
    return serialize_processing_job_result(result)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=2)
def process_catalog_curation_run_task(self, run_id):
    return process_catalog_curation_run(run_id, retry_count=self.request.retries, task_id=self.request.id)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=2)
def refresh_source_catalog_task(self):
    result = process_source_catalog_refresh(retry_count=self.request.retries, task_id=self.request.id)
    return serialize_source_catalog_refresh_result(result)


@shared_task
def run_catalog_automation_schedule_task():
    try:
        return run_due_catalog_automation()
    except (OperationalError, ProgrammingError) as exc:
        if not catalog_automation_schema_not_ready(exc):
            raise

        logger.warning(
            "Catalog automation scheduler skipped because the database schema is not ready yet: %s",
            exc,
        )
        return {"ran": False, "reason": "schema_not_ready"}


@shared_task
def recover_stale_processing_jobs_task():
    remaining_limit = 100
    recovered = 0

    for origin in (SubmissionOrigin.USER, SubmissionOrigin.CURATION):
        if remaining_limit <= 0:
            break
        origin_recovered = recover_stale_processing_jobs(origin=origin, limit=remaining_limit)
        recovered += origin_recovered
        remaining_limit = max(remaining_limit - origin_recovered, 0)

    if remaining_limit > 0:
        try:
            automation_enabled = get_catalog_automation_settings().enabled
        except (OperationalError, ProgrammingError) as exc:
            if not catalog_automation_schema_not_ready(exc):
                raise

            logger.warning(
                "Automation recovery skipped because the database schema is not ready yet: %s",
                exc,
            )
            automation_enabled = False

        if automation_enabled:
            recovered += recover_stale_processing_jobs(
                origin=SubmissionOrigin.AUTOMATION,
                limit=remaining_limit,
            )
    return {"recovered_jobs": recovered}


@shared_task
def send_worker_heartbeat_task():
    """Periodic task that sends heartbeat to the Central Job Engine.

    This task runs every 5 seconds via Celery Beat and publishes
    a heartbeat event to Redis for the Engine to consume.
    """
    try:
        from apps.ingestion.engine.redis_client import create_redis_client
        from apps.ingestion.engine.constants import CH_WORKER_HEARTBEAT
        import json
        import socket
        import os
        from datetime import datetime, timezone

        redis = create_redis_client()
        try:
            hostname = f"celery-beat-{socket.gethostname()}-{os.getpid()}@beat"
            redis.publish(CH_WORKER_HEARTBEAT, json.dumps({
                "hostname": hostname,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
        finally:
            redis.close()
    except Exception:
        logger.exception("Failed to send worker heartbeat to engine")
