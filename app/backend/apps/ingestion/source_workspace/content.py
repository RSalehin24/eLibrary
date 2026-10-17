from apps.catalog.models import Book
from apps.ingestion.services.normalization import plain_text_from_html
from apps.processing.job_models import BackgroundJobKind

SHORT_SOURCE_CHARACTER_COUNT = 1000


def source_content_summary(book):
    if book is None or book.deleted_at:
        return None
    document = Book.objects.only("main_content_html", "content_items").get(pk=book.pk)
    items = document.content_items or []
    body = plain_text_from_html(document.main_content_html)
    chapters = [plain_text_from_html(item.get("content", "")) for item in items]
    count = len(body) + sum(map(len, chapters))
    operation = (
        book.background_jobs.filter(kind=BackgroundJobKind.PROCESS_SOURCE)
        .only("checkpoint")
        .order_by("-created_at", "-pk")
        .first()
    )
    verification = (
        operation.checkpoint.get("source_summary", {}).get("verification")
        if operation is not None
        else None
    )
    return {
        "verification": verification,
        "body_character_count": count,
        "chapter_count": sum(bool(text) for text in chapters),
        "check_completeness": not chapters and count < SHORT_SOURCE_CHARACTER_COUNT,
    }
