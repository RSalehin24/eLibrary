from django.db import transaction

from apps.accounts.models import User
from apps.catalog.locking import lock_entity_kind
from apps.catalog.models import Book
from apps.common.models import LifecycleState
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.jobs.attempts import owned_job
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .queries import current_source_job


def locked_source_job(ownership):
    snapshot = current_source_job(ownership.job_id)
    User.objects.select_for_update(no_key=True).get(pk=snapshot.requested_by_id)
    for kind in ("categories", "contributors", "series"):
        lock_entity_kind(kind)
    job = owned_job(ownership)
    entry = SourceCatalogEntry.objects.select_for_update().get(pk=job.source_record_id)
    current_source_job(job.pk)
    job.source_record = entry
    return job


def checked_source_book(job):
    book = Book.objects.select_for_update().get(pk=job.book_id)
    if (
        book.deleted_at is not None
        or book.state == LifecycleState.ARCHIVED
        or (
            book.state == LifecycleState.PUBLISHED
            and not job.input.get("preserve_publication")
        )
        or book.updated_at.isoformat() != job.checkpoint.get("catalog_revision")
    ):
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_catalog_changed")
    return book


@transaction.atomic
def require_export_authority(ownership):
    return checked_source_book(locked_source_job(ownership))
