from django.db import transaction

from apps.catalog.locking import lock_title
from apps.catalog.models import Book, BookSource
from apps.common.models import LifecycleState, ReviewState
from apps.common.text import normalize_catalog_text
from apps.ingestion.pipeline.curated_persistence import persist_curated_book
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .guards import locked_source_job


def duplicate_books(title):
    return Book.objects.filter(
        normalized_title=normalize_catalog_text(title), deleted_at__isnull=True
    ).order_by("id")


def source_duplicates(result):
    return list(
        duplicate_books(result["projection"]["book_title"]).values_list(
            "pk", flat=True
        )[:20]
    )


@transaction.atomic
def persist_source_book(ownership, result):
    job = locked_source_job(ownership)
    title = result["projection"]["book_title"]
    lock_title(title)
    if job.input.get("resolution") != "separate" and duplicate_books(title).exists():
        return None
    book = Book.objects.create(title=title)
    _source, created = BookSource.objects.select_for_update().get_or_create(
        normalized_source_url=job.source_record.source_url,
        defaults={"book": book, "source_url": job.source_record.source_url},
    )
    if not created:
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_already_linked")
    book, _ = persist_curated_book(
        result, source_url=job.source_record.source_url, target_book=book
    )
    book.state, book.review_state = (
        LifecycleState.PROCESSING,
        ReviewState.PENDING,
    )
    book.save(update_fields=["state", "review_state", "updated_at"])
    entry = job.source_record
    entry.catalog_book = book
    entry.save(update_fields=["catalog_book", "updated_at"])
    job.book = book
    job.checkpoint = {
        **job.checkpoint,
        "source_revision": entry.updated_at.isoformat(),
        "catalog_book_id": str(book.pk),
        "catalog_revision": book.updated_at.isoformat(),
    }
    job.save(update_fields=["book", "checkpoint", "updated_at"])
    return book
