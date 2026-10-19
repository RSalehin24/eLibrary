from datetime import datetime, timedelta

from django.utils import timezone

from apps.common.models import AuditLog
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import JobDispatch

SOURCE_AVAILABILITY_ERRORS = frozenset(
    {
        "source_connection_unavailable",
        "source_request_rejected",
        "source_content_unavailable",
        "source_description_only",
        "source_layout_unknown",
        "source_access_unavailable",
        "source_missing",
        "worker_interrupted",
        "execution_interrupted",
        "source_circuit_open",
    }
)


def source_retry_delay(job):
    if job.error_code == "source_missing":
        return timedelta(days=1)
    if job.error_code in {
        "source_content_unavailable",
        "source_description_only",
        "source_layout_unknown",
        "source_access_unavailable",
    }:
        return timedelta(hours=6)
    failures = job.attempts.filter(error_code__in=SOURCE_AVAILABILITY_ERRORS).count()
    intervals = (15, 60, 300, 3600, 7200, 14400, 21600)
    return timedelta(seconds=intervals[min(max(failures - 1, 0), len(intervals) - 1)])


def schedule_source_availability(job):
    job.state, job.finished_at = "retry_wait", None
    job.generation += 1
    job.available_at = timezone.now() + source_retry_delay(job)
    requested = job.checkpoint.pop("source_retry_after", None)
    if requested:
        job.available_at = max(job.available_at, datetime.fromisoformat(requested))
    if job.error_code in {
        "source_description_only",
        "source_layout_unknown",
        "source_access_unavailable",
        "source_missing",
    }:
        job.checkpoint = {
            key: value
            for key, value in job.checkpoint.items()
            if key
            in {"source_revision", "source_url", "catalog_revision", "catalog_book_id"}
        }
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )


def rebase_changed_source(job):
    from apps.ingestion.source_processing.policy import require_source_url, source_hosts
    from apps.processing.jobs.execution_errors import ExecutionFailure

    if job.book_id:
        return False
    entry = SourceCatalogEntry.objects.select_for_update().get(pk=job.source_record_id)
    try:
        url = require_source_url(entry.source_url, source_hosts())
    except ExecutionFailure as error:
        job.error_code = error.failure.code
        return False
    if url != job.input.get("command", {}).get("source_url") or entry.catalog_book_id:
        return False
    job.checkpoint = {
        "source_revision": entry.updated_at.isoformat(),
        "source_url": url,
    }
    job.state, job.finished_at, job.available_at = "queued", None, timezone.now()
    job.generation += 1
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    AuditLog.objects.create(
        actor=job.requested_by,
        verb="source.rebase_metadata",
        target_type=job._meta.label_lower,
        target_id=str(job.pk),
        payload={"source_revision": entry.updated_at.isoformat()},
    )
    return True
