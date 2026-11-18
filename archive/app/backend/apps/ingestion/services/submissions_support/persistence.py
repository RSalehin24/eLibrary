from django.db import IntegrityError, transaction

from apps.catalog.models import Book, BookSource, ContributorRole, MetadataVersion
from apps.common.models import AuditLog, LifecycleState, ReviewState
from apps.ingestion.models import ResolutionStatus, SubmissionStatus


def complete_processed_submission(
    submission,
    book,
    normalized_url,
    *,
    ensure_preview_session_fn,
    source="scrape",
    sync_deduplicated_submissions_fn,
):
    submission.linked_book = book
    submission.duplicate_of_book = None
    submission.resolved_url = normalized_url
    submission.resolution_status = ResolutionStatus.RESOLVED
    submission.resolution_confidence = max(submission.resolution_confidence, 1.0)
    submission.status = SubmissionStatus.READY
    submission.review_state = book.review_state
    submission.error_message = ""
    submission.raw_payload = {
        **submission.raw_payload,
        "normalized_url": normalized_url,
        "linked_book_slug": book.slug,
        "processing_source": source,
        "served_from_database": False,
    }
    submission.save(update_fields=["linked_book", "duplicate_of_book", "resolved_url", "resolution_status", "resolution_confidence", "status", "review_state", "error_message", "raw_payload", "updated_at"])
    sync_deduplicated_submissions_fn(submission)

    if submission.submitter_id:
        ensure_preview_session_fn(submission.submitter, book, submission=submission)

    AuditLog.objects.create(
        actor=submission.submitter,
        verb="submission.processed",
        target_type="BookSubmission",
        target_id=str(submission.id),
        payload={"book_id": str(book.id), "source": source},
    )


def sync_metadata_relations(book, normalized, *, replace_book_relations_fn):
    replace_book_relations_fn(
        book,
        contributors=normalized["contributors"],
        series_names=normalized["series"],
        category_names=normalized["categories"],
    )


def persist_scraped_book(
    submission,
    scraped_data,
    *,
    clean_extracted_dedication_html_fn,
    find_deleted_book_by_title_fn,
    find_existing_book_by_source_url_fn,
    job,
    normalize_scraped_book_fn,
    normalize_source_url_fn,
    sync_metadata_relations_fn,
    target_book=None,
):
    normalized = normalize_scraped_book_fn(scraped_data)
    cleaned_dedication_html = clean_extracted_dedication_html_fn(scraped_data.get("dedication", ""))
    cover_source_url = scraped_data.get("cover") or ""
    normalized_submission_source_url = normalize_source_url_fn(submission.resolved_url)
    raw_scraped_metadata = {
        **normalized["raw_strings"],
        "source_url": submission.resolved_url,
    }

    def apply_scraped_fields(book):
        book.deleted_at = None
        book.state = LifecycleState.READY
        book.review_state = ReviewState.PENDING
        book.raw_scraped_metadata = raw_scraped_metadata
        book.raw_scrape_payload = scraped_data
        book.main_content_html = scraped_data.get("main_content", "")
        book.book_info_html = scraped_data.get("book_info", "")
        book.dedication_html = cleaned_dedication_html
        book.toc = scraped_data.get("toc", [])
        book.content_items = scraped_data.get("content_items", [])
        book.cover_source_url = cover_source_url

    existing_book = target_book or find_deleted_book_by_title_fn(scraped_data["book_title"])
    if existing_book:
        book = existing_book
        apply_scraped_fields(book)
        book.save(update_fields=["deleted_at", "state", "review_state", "raw_scraped_metadata", "raw_scrape_payload", "main_content_html", "book_info_html", "dedication_html", "toc", "content_items", "cover_source_url", "updated_at"])
    else:
        create_kwargs = {
            "title": scraped_data["book_title"],
            "state": LifecycleState.READY,
            "review_state": ReviewState.PENDING,
            "raw_scraped_metadata": raw_scraped_metadata,
            "raw_scrape_payload": scraped_data,
            "main_content_html": scraped_data.get("main_content", ""),
            "book_info_html": scraped_data.get("book_info", ""),
            "dedication_html": cleaned_dedication_html,
            "toc": scraped_data.get("toc", []),
            "content_items": scraped_data.get("content_items", []),
            "cover_source_url": cover_source_url,
        }
        try:
            with transaction.atomic():
                book = Book.objects.create(**create_kwargs)
        except IntegrityError:
            if not normalized_submission_source_url:
                raise
            book = find_existing_book_by_source_url_fn(normalized_submission_source_url)
            if book is None:
                raise
            apply_scraped_fields(book)
            book.save(update_fields=["deleted_at", "state", "review_state", "raw_scraped_metadata", "raw_scrape_payload", "main_content_html", "book_info_html", "dedication_html", "toc", "content_items", "cover_source_url", "updated_at"])

    sync_metadata_relations_fn(book, normalized)
    BookSource.objects.update_or_create(
        normalized_source_url=normalized_submission_source_url,
        defaults={
            "book": book,
            "source_url": submission.resolved_url,
            "source_title": scraped_data.get("book_title", ""),
            "raw_metadata": raw_scraped_metadata,
        },
    )
    MetadataVersion.objects.create(book=book, snapshot=scraped_data, source="scrape")
    return book


def export_payload_from_book(book, scraped_data):
    author_names = [
        relation.contributor.name
        for relation in book.book_contributors.all()
        if relation.role == ContributorRole.AUTHOR
    ]
    series_names = [relation.series.name for relation in book.book_series.all()]
    category_names = [relation.category.name for relation in book.book_categories.all()]

    return {
        "book_title": book.title,
        "author": author_names or scraped_data.get("author", ""),
        "series": series_names or scraped_data.get("series", ""),
        "book_type": category_names or scraped_data.get("book_type", ""),
        "cover": scraped_data.get("cover") or book.cover_source_url or "",
        "cover_source_url": book.cover_source_url or scraped_data.get("cover_source_url", ""),
        "main_content": book.main_content_html or "",
        "book_info": book.book_info_html or "",
        "dedication": book.dedication_html or "",
        "front_sections": (
            (book.raw_scrape_payload.get("front_sections") if isinstance(book.raw_scrape_payload, dict) else None)
            or scraped_data.get("front_sections", [])
        ),
        "back_sections": (
            (book.raw_scrape_payload.get("back_sections") if isinstance(book.raw_scrape_payload, dict) else None)
            or scraped_data.get("back_sections", [])
        ),
        "toc": book.toc or [],
        "content_items": book.content_items or [],
        "output_folder": scraped_data["output_folder"],
    }
