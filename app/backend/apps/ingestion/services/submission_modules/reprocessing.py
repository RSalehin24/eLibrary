from apps.catalog.models import Book
from apps.common.models import LifecycleState


def prepare_regeneration(job):
    identifier = job.payload.get("reprocess_book_id") or job.book_id or job.submission.linked_book_id
    if identifier is None:
        raise ValueError("The target book for regeneration is unavailable.")
    book = Book.objects.filter(pk=identifier, deleted_at__isnull=True).first()
    if book is None:
        raise ValueError("The target book for regeneration is unavailable.")
    if book.state != LifecycleState.PROCESSING:
        book.state = LifecycleState.PROCESSING
        book.save(update_fields=["state", "updated_at"])
    return book
