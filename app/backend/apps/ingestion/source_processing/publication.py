from django.db import transaction

from apps.catalog.editorial.source_publication import source_publication_problem
from apps.common.models import AuditLog, LifecycleState, ReviewState
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .guards import checked_source_book, locked_source_job
from .reading_preparation import checked_source_asset


@transaction.atomic
def publish_verified_source(ownership):
    job = locked_source_job(ownership)
    book = checked_source_book(job)
    checked_source_asset(job)
    verification = job.checkpoint.get("source_summary", {}).get("verification", {})
    if not verification.get("verified") or not job.checkpoint.get("exports_verified"):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_verification_missing")
    if source_publication_problem(book, job.pk):
        raise ExecutionFailure(FailureKind.TRANSIENT, "source_publication_not_ready")
    if not checkpoint_attempt(ownership, job.checkpoint, "publishing_source"):
        return False
    book.state, book.review_state = LifecycleState.PUBLISHED, ReviewState.APPROVED
    book.save(update_fields=["state", "review_state", "updated_at"])
    AuditLog.objects.create(
        actor=job.requested_by,
        verb="catalog.book.auto_publish",
        target_type=book._meta.label_lower,
        target_id=str(book.pk),
        payload={"operation_id": str(job.pk), "verification": verification},
    )
    return checkpoint_attempt(
        ownership,
        {
            **job.checkpoint,
            "auto_published": True,
            "catalog_revision": book.updated_at.isoformat(),
        },
        "source_published",
    )


@transaction.atomic
def completed_source_publication(ownership):
    job = locked_source_job(ownership)
    book = job.book
    checked_source_asset(job)
    if (
        book is None
        or book.deleted_at
        or book.state != LifecycleState.PUBLISHED
        or book.updated_at.isoformat() != job.checkpoint.get("catalog_revision")
        or source_publication_problem(book, job.pk)
    ):
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_catalog_changed")
    return checkpoint_attempt(ownership, job.checkpoint, "source_published")
