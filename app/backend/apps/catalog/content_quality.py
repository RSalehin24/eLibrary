from django.db import transaction

from apps.catalog.models import Book
from apps.common.models import AuditLog, LifecycleState

QUALITY_KEY = "source_quality"


def book_is_quarantined(book):
    if book is None:
        return False
    return book.source_quality_state == "quarantined"


@transaction.atomic
def quarantine_book(book, evidence, actor=None):
    current = Book.objects.select_for_update().get(pk=book.pk)
    quality = {**evidence, "state": "quarantined"}
    if current.raw_scraped_metadata.get(QUALITY_KEY) == quality:
        return current
    current.source_quality_state = "quarantined"
    current.raw_scraped_metadata = {
        **current.raw_scraped_metadata,
        QUALITY_KEY: quality,
    }
    if current.state == LifecycleState.PUBLISHED:
        current.state = LifecycleState.PROCESSING
    current.save(
        update_fields=[
            "raw_scraped_metadata",
            "source_quality_state",
            "state",
            "updated_at",
        ]
    )
    AuditLog.objects.create(
        actor=actor,
        verb="catalog.book.quarantine",
        target_type=current._meta.label_lower,
        target_id=str(current.pk),
        payload=evidence,
    )
    return current


def mark_source_verified(book, evidence):
    book.source_quality_state = "verified"
    book.raw_scraped_metadata = {
        **book.raw_scraped_metadata,
        QUALITY_KEY: {**evidence, "state": "verified"},
    }
