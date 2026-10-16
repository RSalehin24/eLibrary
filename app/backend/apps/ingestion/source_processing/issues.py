from django.shortcuts import get_object_or_404

from apps.catalog.models import Book
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
)

from .summary import source_document_available


def available_source_choices(job):
    if job.state not in {BackgroundJobState.NEEDS_ATTENTION, BackgroundJobState.FAILED}:
        return []
    choices = ["cancel"]
    entry = job.source_record
    expected = job.checkpoint.get(
        "source_revision", job.input["command"]["source_revision"]
    )
    unchanged = entry is not None and entry.updated_at.isoformat() == expected
    if not job.book_id:
        return (
            ["retry", "link", "separate", *choices]
            if unchanged
            and job.error_code == "source_duplicate"
            and source_document_available(job)
            else ["retry", *choices]
        )
    book = Book.objects.only("updated_at", "state", "deleted_at").get(pk=job.book_id)
    if (
        unchanged
        and source_document_available(job)
        and book.deleted_at is None
        and book.state != "published"
        and book.updated_at.isoformat() == job.checkpoint.get("catalog_revision")
    ):
        return ["resume_preparation", *choices]
    return choices


def source_issue(identifier):
    job = get_object_or_404(
        BackgroundJob.objects.select_related("source_record").defer(
            "source_record__raw_data"
        ),
        pk=identifier,
        kind=BackgroundJobKind.PROCESS_SOURCE,
    )
    summary = job.checkpoint.get("source_summary", {})
    candidates = Book.objects.filter(
        pk__in=job.checkpoint.get("duplicate_book_ids", []), deleted_at__isnull=True
    ).order_by("id")
    return {
        "id": job.pk,
        "expected_updated_at": job.updated_at,
        "title": summary.get(
            "title", job.source_record.title if job.source_record else ""
        ),
        "author_line": summary.get("author_line", ""),
        "validation_status": summary.get("validation_status", ""),
        "error_count": summary.get("error_count", 0),
        "warning_count": summary.get("warning_count", 0),
        "candidates": list(
            candidates.values("id", "title", "slug", "catalog_code", "updated_at")[:20]
        ),
        "available_choices": available_source_choices(job),
    }
