from apps.catalog.models import BookSource
from apps.common.models import AuditLog, LifecycleState
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.ingestion.source_processing.policy import require_source_url, source_hosts
from apps.processing.job_models import SOURCE_ACTIVE_STATES
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.requests import require_processing_manager
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .service import EditorialConflict, record_metadata_version, revision_checked_book


def unfinished_book_work(book):
    return (
        book.background_jobs.filter(state__in=SOURCE_ACTIVE_STATES).exists()
        or book.processing_jobs.filter(status__in=["queued", "processing"]).exists()
    )


def configured_book_source(book):
    source = BookSource.objects.filter(book=book).first()
    if source is None:
        return None
    try:
        url = require_source_url(source.normalized_source_url, source_hosts())
        return url if normalize_source_url(url) == url else None
    except (ExecutionFailure, ValueError):
        return None


def regeneration_problem(actor, book):
    if book.record_type == "manual":
        return "paper_book"
    if not processing_available(actor):
        return "processing_access_required"
    if unfinished_book_work(book):
        return "unfinished_work"
    return None if configured_book_source(book) else "source_unavailable"


def book_controls(actor, book):
    active = book.background_jobs.filter(state__in=SOURCE_ACTIVE_STATES).first()
    problem = regeneration_problem(actor, book)
    return {
        "book_revision": book.updated_at,
        "can_regenerate": problem is None,
        "regeneration_problem": problem,
        "can_remove": not unfinished_book_work(book),
        "active_operation_id": active.pk
        if active and processing_available(actor)
        else None,
    }


def processing_available(actor):
    try:
        require_processing_manager(actor)
    except PermissionDenied:
        return False
    return True


@transaction.atomic
def remove_managed_book(actor, book_id, expected):
    book = revision_checked_book(actor, book_id, expected)
    if unfinished_book_work(book):
        raise EditorialConflict(
            "Finish or cancel the book's current work before removing it."
        )
    record_metadata_version(book, actor)
    book.deleted_at, book.state = timezone.now(), LifecycleState.SOFT_DELETED
    book.save(update_fields=["deleted_at", "state", "updated_at"])
    AuditLog.objects.create(
        actor=actor,
        verb="catalog.book.remove",
        target_type=book._meta.label_lower,
        target_id=str(book.pk),
    )
