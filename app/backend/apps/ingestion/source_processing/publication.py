from django.db import transaction

from apps.catalog.content_quality import mark_source_verified
from apps.catalog.editorial.source_publication import source_publication_problem
from apps.common.models import AuditLog, LifecycleState
from apps.ingestion.source_discovery.updates import save_published_probe
from apps.ingestion.source_workspace.update_probe import cached_source_probe
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .asset_publication import commit_source_assets
from .editions import record_published_edition
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
    if not job.checkpoint.get("assets_published"):
        if not commit_source_assets(ownership, job.checkpoint["staged_assets"]):
            return False
        job = locked_source_job(ownership)
        book = checked_source_book(job)
    if source_publication_problem(book, job.pk):
        raise ExecutionFailure(FailureKind.TRANSIENT, "source_publication_not_ready")
    if not checkpoint_attempt(ownership, job.checkpoint, "publishing_source"):
        return False
    book.state = LifecycleState.PUBLISHED
    mark_source_verified(book, verification)
    book.save(
        update_fields=[
            "state",
            "raw_scraped_metadata",
            "source_quality_state",
            "updated_at",
        ]
    )
    probe = cached_source_probe(job, job.source_record.source_url)
    if probe:
        save_published_probe(job.source_record, probe)
    record_published_edition(job)
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
