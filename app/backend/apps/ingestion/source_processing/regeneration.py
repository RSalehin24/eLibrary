from datetime import UTC

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.catalog.discovery.management import metadata_managed_books
from apps.catalog.editorial.lifecycle import (
    configured_book_source,
    unfinished_book_work,
)
from apps.catalog.editorial.service import (
    EditorialConflict,
    record_metadata_version,
    revision_checked_book,
)
from apps.catalog.models import MetadataVersion
from apps.common.models import AuditLog, LifecycleState, ReviewState
from apps.common.text import normalize_catalog_text
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.curated_persistence import (
    _count_empty_toc_chapters,
    persist_curated_document,
)
from apps.processing.job_models import BackgroundJob, BackgroundJobKind, JobDispatch
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .commands import matching_source_command


def regeneration_command(book, values, url):
    return {
        "book_id": str(book.pk),
        "book_revision": values["expected_updated_at"].astimezone(UTC).isoformat(),
        "source_url": url,
    }


def regeneration_entry(book, url):
    entry, _ = SourceCatalogEntry.objects.select_for_update().get_or_create(
        source_url=url,
        defaults={
            "title": book.title,
            "normalized_title": normalize_catalog_text(book.title),
            "normalized_display": normalize_catalog_text(book.title),
            "catalog_book": book,
        },
    )
    if entry.catalog_book_id and entry.catalog_book_id != book.pk:
        raise JobStateConflict(
            "The source is linked to another book. Inspect it before regeneration."
        )
    return entry


@transaction.atomic
def request_book_regeneration(actor, book_id, values):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    snapshot = get_object_or_404(metadata_managed_books(actor), pk=book_id)
    url = configured_book_source(snapshot)
    if snapshot.record_type != "digital" or not url:
        raise ValidationError(
            "Regeneration requires a digital book from the configured website."
        )
    command = regeneration_command(snapshot, values, url)
    existing = matching_source_command(actor, values["operation_id"], command)
    if existing is not None:
        return existing
    entry = regeneration_entry(snapshot, url)
    book = revision_checked_book(actor, book_id, values["expected_updated_at"])
    if unfinished_book_work(book):
        raise EditorialConflict(
            "Finish or cancel the book's current work before regeneration."
        )
    record_metadata_version(book, actor)
    preserve_publication = (
        book.state == LifecycleState.PUBLISHED
        and book.source_quality_state != "quarantined"
    )
    if not preserve_publication:
        book.state, book.review_state, book.editorial_reviewed_at = (
            LifecycleState.PROCESSING,
            ReviewState.PENDING,
            None,
        )
        book.save(
            update_fields=[
                "state",
                "review_state",
                "editorial_reviewed_at",
                "updated_at",
            ]
        )
    try:
        with transaction.atomic():
            job = BackgroundJob.objects.create(
                id=values["operation_id"],
                requested_by=actor,
                book=book,
                source_record=entry,
                kind=BackgroundJobKind.PROCESS_SOURCE,
                input={
                    "command": command,
                    "regenerate_book": True,
                    "preserve_publication": preserve_publication,
                },
                available_at=timezone.now(),
                checkpoint={
                    "source_revision": entry.updated_at.isoformat(),
                    "catalog_revision": book.updated_at.isoformat(),
                },
            )
            JobDispatch.objects.create(
                job=job, generation=job.generation, available_at=job.available_at
            )
    except IntegrityError as error:
        raise JobStateConflict(
            "Another source operation is active. Inspect it before continuing."
        ) from error
    AuditLog.objects.create(
        actor=actor,
        verb="catalog.book.regenerate",
        target_type=book._meta.label_lower,
        target_id=str(book.pk),
        payload={"operation_id": str(job.pk)},
    )
    return job


def commit_regenerated_content(job, book, result):
    projection = result["projection"]
    fields = {
        "main_content_html": "main_content",
        "book_info_html": "book_info",
        "dedication_html": "dedication",
        "toc": "toc",
        "content_items": "content_items",
    }
    MetadataVersion.objects.create(
        book=book,
        snapshot={field: getattr(book, field) for field in fields},
        source="before_regeneration",
    )
    for field, key in fields.items():
        setattr(
            book,
            field,
            projection.get(key, [] if key in {"toc", "content_items"} else ""),
        )
    document = persist_curated_document(result, book=book)
    MetadataVersion.objects.create(
        book=book, snapshot=document.document, source="regeneration"
    )
    book.empty_chapters_count = _count_empty_toc_chapters(book.toc)
    book.save(update_fields=[*fields, "empty_chapters_count", "updated_at"])
    job.checkpoint = {
        **job.checkpoint,
        "catalog_revision": book.updated_at.isoformat(),
        "content_committed": True,
    }
