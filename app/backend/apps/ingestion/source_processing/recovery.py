from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.editorial.service import revision_checked_book
from apps.catalog.models import Book
from apps.common.models import AuditLog, LifecycleState
from apps.processing.job_models import BackgroundJob, JobDispatch, RequestedJobAction
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .queries import current_source_job
from .resolution import resolve_source_job
from .storage import read_artifact, write_artifact


@transaction.atomic
def complete_pending_source(actor, identifier):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    current_source_job(identifier)
    job = BackgroundJob.objects.select_for_update().get(pk=identifier)
    if job.state == "queued" and job.input.get("complete_pending_publication"):
        return job
    if (
        job.state != "succeeded"
        or not job.book_id
        or not job.checkpoint.get("document_ref")
    ):
        raise JobStateConflict(
            "Only a completed source preparation can continue to publication."
        )
    book = Book.objects.get(pk=job.book_id)
    book = revision_checked_book(actor, book.pk, book.updated_at)
    if book.deleted_at or book.state in {
        LifecycleState.PUBLISHED,
        LifecycleState.ARCHIVED,
    }:
        raise JobStateConflict("This book is already published or unavailable.")
    if job.checkpoint.get("catalog_revision") != book.updated_at.isoformat():
        raise JobStateConflict(
            "The book changed after preparation. Regenerate it from its current record."
        )
    book.state = LifecycleState.PROCESSING
    book.save(update_fields=["state", "updated_at"])
    job.checkpoint = {**job.checkpoint, "catalog_revision": book.updated_at.isoformat()}
    job.input = {**job.input, "complete_pending_publication": True}
    job.generation += 1
    job.state, job.error_code, job.finished_at = "queued", "", None
    job.requested_action, job.available_at = RequestedJobAction.NONE, timezone.now()
    job.save()
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    AuditLog.objects.create(
        actor=actor,
        verb="source.complete_preparation",
        target_type=job._meta.label_lower,
        target_id=str(job.pk),
    )
    return job


@transaction.atomic
def restart_repaired_source(actor, identifier):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    snapshot = BackgroundJob.objects.select_related("source_record").get(pk=identifier)
    if (
        snapshot.kind != "process_source"
        or snapshot.source_record is None
        or snapshot.book_id
    ):
        raise JobStateConflict("This recovery requires an unlinked source operation.")
    reference = snapshot.checkpoint.get("page_cache_ref")
    pages = read_artifact(snapshot.pk, reference) if reference else {}
    pages.pop(snapshot.source_record.source_url, None)
    job = resolve_source_job(
        actor,
        identifier,
        {"choice": "retry", "expected_updated_at": snapshot.updated_at},
    )
    if pages and snapshot.input["command"]["source_url"] == job.checkpoint.get(
        "source_url"
    ):
        size = sum(
            len(read_artifact(job.pk, value).encode()) for value in pages.values()
        )
        job.checkpoint = {
            **job.checkpoint,
            "page_cache_ref": write_artifact(job.pk, pages),
            "cache_bytes": size,
            "pages_fetched": len(pages),
        }
        job.save(update_fields=["checkpoint", "updated_at"])
    return job
