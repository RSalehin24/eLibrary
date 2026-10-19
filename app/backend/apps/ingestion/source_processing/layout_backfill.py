from django.db import transaction

from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure

from .documents import read_source_result
from .layout import source_layout


def retained_job_layout(job):
    reference = job.checkpoint.get("document_ref")
    if not reference:
        return None
    try:
        result = read_source_result(job.pk, reference)
    except (OSError, ValueError, ExecutionFailure):
        return None
    return source_layout(result.get("source_snapshot", {}))


@transaction.atomic
def apply_job_layout(job, layout):
    current = BackgroundJob.objects.select_for_update().get(pk=job.pk)
    if current.state == "running" or current.checkpoint.get(
        "document_ref"
    ) != job.checkpoint.get("document_ref"):
        return "changed"
    summary = {**current.checkpoint.get("source_summary", {}), "layout": layout}
    current.checkpoint = {**current.checkpoint, "source_summary": summary}
    # Diagnostic backfill does not change the operation or invalidate control revisions.
    current.save(update_fields=["checkpoint"])
    return "updated"


def backfill_job_layout(job, apply=False):
    if job.kind != "process_source" or job.state == "running":
        return "skipped"
    layout = retained_job_layout(job)
    if not layout:
        return "unavailable"
    if job.checkpoint.get("source_summary", {}).get("layout") == layout:
        return "unchanged"
    return apply_job_layout(job, layout) if apply else "would_update"
