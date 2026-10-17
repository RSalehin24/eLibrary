from rest_framework.exceptions import PermissionDenied

from apps.catalog.discovery.management import metadata_managed_books
from apps.catalog.models import BookSource
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from apps.processing.jobs.requests import require_processing_manager


def current_source_job(identifier):
    job = (
        BackgroundJob.objects.select_related("requested_by", "source_record")
        .defer("source_record__raw_data")
        .get(pk=identifier)
    )
    actor = job.requested_by
    if job.source_record is None:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_record_missing")
    try:
        if actor is None:
            raise PermissionDenied()
        require_processing_manager(actor)
    except PermissionDenied:
        raise ExecutionFailure(FailureKind.PERMANENT, "permission_revoked") from None
    expected = job.checkpoint.get(
        "source_revision", job.input["command"].get("source_revision")
    )
    if job.source_record.updated_at.isoformat() != expected:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_record_changed")
    if job.input.get("regenerate_book"):
        book = (
            metadata_managed_books(actor)
            .filter(pk=job.book_id)
            .only("updated_at")
            .first()
        )
        if book is None:
            raise ExecutionFailure(FailureKind.PERMANENT, "permission_revoked")
        if book.updated_at.isoformat() != job.checkpoint.get("catalog_revision"):
            raise ExecutionFailure(FailureKind.UNCERTAIN, "source_catalog_changed")
    return job


def linked_source_book(entry):
    if entry.catalog_book_id:
        return entry.catalog_book
    source = (
        BookSource.objects.select_related("book")
        .filter(normalized_source_url=entry.source_url)
        .first()
    )
    return source.book if source else None
