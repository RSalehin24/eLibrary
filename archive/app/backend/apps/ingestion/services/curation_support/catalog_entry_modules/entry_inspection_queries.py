from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from apps.catalog.models import BookSource, GeneratedAssetStatus, GeneratedAssetType
from apps.common.models import LifecycleState
from apps.ingestion.models import (
    BookSubmission,
    CatalogCurationMode,
    CatalogCurationTrigger,
    JobStatus,
    ProcessingJob,
    SubmissionOrigin,
)

REQUIRED_READY_ASSETS = (GeneratedAssetType.HTML, GeneratedAssetType.EPUB)
FAILED_AUTOMATION_RETRY_COOLDOWN = timedelta(hours=6)
SOURCE_LOOKUP_CHUNK_SIZE = 500
HEAVY_BOOK_LIST_FIELDS = (
    "summary",
    "raw_scraped_metadata",
    "raw_scrape_payload",
    "main_content_html",
    "book_info_html",
    "dedication_html",
    "toc",
    "content_items",
)
OVERVIEW_CURATION_STATUSES = {"failed", "requeued"}


def related_book_list_defer_fields(*prefixes):
    return [
        f"{prefix}{field}"
        for prefix in prefixes
        for field in HEAVY_BOOK_LIST_FIELDS
    ]


def iter_source_url_chunks(source_urls, chunk_size=SOURCE_LOOKUP_CHUNK_SIZE):
    unique_urls = [url for url in dict.fromkeys(source_urls or ()) if url]
    for index in range(0, len(unique_urls), chunk_size):
        yield unique_urls[index : index + chunk_size]


def source_catalog_book_source_map(source_urls):
    book_source_map = {}

    for source_url_chunk in iter_source_url_chunks(source_urls):
        book_sources = (
            BookSource.objects.filter(normalized_source_url__in=source_url_chunk)
            .select_related("book")
            .defer(*related_book_list_defer_fields("book__"))
            .prefetch_related(
                "book__generated_assets",
                Prefetch(
                    "book__processing_jobs",
                    queryset=ProcessingJob.objects.defer("payload").order_by(
                        "-finished_at",
                        "-started_at",
                        "-updated_at",
                        "-created_at",
                    ),
                ),
                "book__book_categories__category",
            )
        )
        book_source_map.update(
            {
                book_source.normalized_source_url: book_source
                for book_source in book_sources
            }
        )

    return book_source_map


def source_catalog_submission_map(source_urls):
    submission_map = {}

    for source_url_chunk in iter_source_url_chunks(source_urls):
        queryset = (
            BookSubmission.objects.filter(resolved_url__in=source_url_chunk)
            .select_related(
                "linked_book",
                "canonical_submission",
                "canonical_submission__linked_book",
            )
            .defer(
                "raw_payload",
                "canonical_submission__raw_payload",
                *related_book_list_defer_fields(
                    "linked_book__",
                    "canonical_submission__linked_book__",
                ),
            )
            .prefetch_related(
                Prefetch(
                    "processing_jobs",
                    queryset=ProcessingJob.objects.defer("payload").order_by(
                        "-finished_at",
                        "-started_at",
                        "-updated_at",
                        "-created_at",
                    ),
                ),
                Prefetch(
                    "canonical_submission__processing_jobs",
                    queryset=ProcessingJob.objects.defer("payload").order_by(
                        "-finished_at",
                        "-started_at",
                        "-updated_at",
                        "-created_at",
                    ),
                ),
            )
            .order_by("-updated_at", "-created_at")
        )

        for submission in queryset:
            submission_map.setdefault(submission.resolved_url, submission)

    return submission_map


def inspect_source_catalog_entry_batch(entries):
    entries = list(entries or [])
    if not entries:
        return []

    source_urls = [entry.source_url for entry in entries]
    source_map = source_catalog_book_source_map(source_urls)
    submission_map = source_catalog_submission_map(source_urls)
    return [
        inspect_source_catalog_entry(entry, source_map, submission_map)
        for entry in entries
    ]


def iter_source_catalog_entry_inspections(queryset, chunk_size=None):
    chunk_size = chunk_size or SOURCE_LOOKUP_CHUNK_SIZE
    entry_iterable = (
        queryset.iterator(chunk_size=chunk_size)
        if hasattr(queryset, "iterator")
        else iter(queryset)
    )
    entry_chunk = []

    for entry in entry_iterable:
        entry_chunk.append(entry)
        if len(entry_chunk) >= chunk_size:
            yield from inspect_source_catalog_entry_batch(entry_chunk)
            entry_chunk = []

    if entry_chunk:
        yield from inspect_source_catalog_entry_batch(entry_chunk)


def book_has_required_assets(book):
    asset_statuses = {asset.asset_type: asset.status for asset in book.generated_assets.all()}
    return all(asset_statuses.get(asset_type) == GeneratedAssetStatus.READY for asset_type in REQUIRED_READY_ASSETS)


def root_submission(submission):
    return submission.canonical_submission or submission


def latest_processing_job_for_submission(submission):
    if submission is None:
        return None
    canonical_submission = root_submission(submission)
    return canonical_submission.processing_jobs.first()


def latest_activity_at(entry, latest_submission, latest_job, local_book):
    return (
        (latest_job.finished_at if latest_job else None)
        or (latest_job.started_at if latest_job else None)
        or (latest_job.updated_at if latest_job else None)
        or (latest_submission.updated_at if latest_submission else None)
        or (local_book.updated_at if local_book else None)
        or entry.last_seen_at
    )


def inspect_source_catalog_entry(entry, source_map, submission_map=None):
    submission_map = submission_map or {}
    book_source = source_map.get(entry.source_url)
    local_book = book_source.book if book_source and book_source.book_id else None
    latest_submission = submission_map.get(entry.source_url)
    latest_job = local_book.processing_jobs.first() if local_book else latest_processing_job_for_submission(latest_submission)

    if local_book and local_book.deleted_at:
        status = "deleted"
    elif latest_job and latest_job.status in {JobStatus.QUEUED, JobStatus.PROCESSING}:
        status = "processing"
    elif latest_submission and latest_submission.status in {"pending_resolution", "queued", "processing"}:
        status = "processing"
    elif latest_job and latest_job.status == JobStatus.CANCELLED:
        status = "stopped"
    elif latest_submission and latest_submission.status == "cancelled":
        status = "stopped"
    elif latest_job and latest_job.status == JobStatus.FAILED:
        status = "failed"
    elif latest_submission and latest_submission.status in {"failed", "needs_review", "duplicate"}:
        status = "failed"
    elif not local_book:
        status = "new"
    elif local_book.state != LifecycleState.READY or not book_has_required_assets(local_book):
        status = "unfinished"
    else:
        status = "ready"

    return {
        "entry": entry,
        "book_source": book_source,
        "local_book": local_book,
        "latest_submission": latest_submission,
        "latest_job": latest_job,
        "curation_status": status,
        "activity_at": latest_activity_at(entry, latest_submission, latest_job, local_book),
    }


def serialize_source_catalog_entry_inspection(inspection):
    entry = inspection["entry"]
    local_book = inspection["local_book"]
    latest_submission = inspection["latest_submission"]
    latest_job = inspection["latest_job"]
    raw_data = entry.raw_data or {}
    source_categories = (raw_data.get("category") or raw_data.get("book_type") or "").strip()
    local_categories = ""
    if local_book and not local_book.deleted_at:
        local_categories = ", ".join(
            relation.category.name
            for relation in local_book.book_categories.all()
            if relation.category_id and relation.category and relation.category.name
        )
    return {
        "id": str(entry.id),
        "title": entry.title,
        "author_line": entry.author_line,
        "categories": source_categories or local_categories,
        "source_url": entry.source_url,
        "created_at": entry.created_at,
        "last_seen_at": entry.last_seen_at,
        "curation_status": inspection["curation_status"],
        "local_book_slug": local_book.slug if local_book and not local_book.deleted_at else "",
        "local_book_title": local_book.title if local_book and not local_book.deleted_at else "",
        "local_book_state": local_book.state if local_book and not local_book.deleted_at else "",
        "latest_submission_status": latest_submission.status if latest_submission else "",
        "latest_job_status": latest_job.status if latest_job else "",
        "latest_job_error": latest_job.last_error if latest_job else "",
        "activity_at": inspection["activity_at"],
        "updated_at": local_book.updated_at if local_book and not local_book.deleted_at else None,
    }
