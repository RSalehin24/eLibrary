from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Book
from apps.common.models import AuditLog
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
    JobDispatch,
    RequestedJobAction,
)
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .guards import checked_source_book
from .issues import available_source_choices
from .policy import require_source_url, source_hosts

SOURCE_RETRY_ALLOWANCE = 3


def renew_attempt_budget(job):
    job.max_attempts = SOURCE_RETRY_ALLOWANCE
    job.input = {**job.input, "retry_after_attempt": job.attempt_count}


def require_resolution_revision(job, values):
    if job.updated_at != values["expected_updated_at"]:
        raise JobStateConflict()
    if job.state not in {BackgroundJobState.NEEDS_ATTENTION, BackgroundJobState.FAILED}:
        raise JobStateConflict("This source operation is not awaiting a decision.")


def link_duplicate(job, entry, values):
    if job.error_code != "source_duplicate":
        raise JobStateConflict(
            "Only a confirmed duplicate can link to an existing book."
        )
    identifier = str(values.get("book_id", ""))
    if identifier not in job.checkpoint.get("duplicate_book_ids", []):
        raise JobStateConflict("Choose a book from the reviewed candidates.")
    book = get_object_or_404(
        Book.objects.select_for_update().filter(deleted_at__isnull=True), pk=identifier
    )
    if book.updated_at != values["expected_book_updated_at"]:
        raise JobStateConflict(
            "The candidate book changed. Inspect its current metadata before linking."
        )
    entry.catalog_book = book
    entry.save(update_fields=["catalog_book", "updated_at"])
    job.book = book
    job.state, job.finished_at = BackgroundJobState.SUCCEEDED, timezone.now()
    job.checkpoint = {
        **job.checkpoint,
        "resolution": "linked_existing",
        "source_revision": entry.updated_at.isoformat(),
    }


def restart_source_job(job, entry, choice):
    if job.book_id and choice != "resume_preparation":
        raise JobStateConflict(
            "Resume the existing draft instead of collecting a second book."
        )
    if choice == "resume_preparation":
        checked_source_book(job)
        if not job.checkpoint.get("document_ref"):
            raise JobStateConflict("The draft has no recoverable source document.")
    if choice == "separate" and job.error_code != "source_duplicate":
        raise JobStateConflict(
            "A separate book decision requires a reviewed duplicate."
        )
    require_source_url(entry.source_url, source_hosts())
    renew_attempt_budget(job)
    job.input = {**job.input, "resolution": choice}
    if choice == "retry":
        job.checkpoint = {
            "source_revision": entry.updated_at.isoformat(),
            "source_url": entry.source_url,
        }
    job.generation += 1
    job.state, job.error_code, job.finished_at = BackgroundJobState.QUEUED, "", None
    job.available_at = timezone.now()
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )


@transaction.atomic
def resolve_source_job(actor, identifier, values):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    job = get_object_or_404(
        BackgroundJob.objects.select_for_update(),
        pk=identifier,
        kind=BackgroundJobKind.PROCESS_SOURCE,
    )
    require_resolution_revision(job, values)
    if job.source_record_id is None:
        raise JobStateConflict("This operation has no source record.")
    entry = SourceCatalogEntry.objects.select_for_update().get(pk=job.source_record_id)
    job.source_record = entry
    if values["choice"] not in available_source_choices(job):
        raise JobStateConflict(
            "Inspect the current source and catalog record before choosing this action."
        )
    expected_source = job.checkpoint.get(
        "source_revision", job.input["command"]["source_revision"]
    )
    if (
        values["choice"] in {"link", "separate", "resume_preparation"}
        and entry.updated_at.isoformat() != expected_source
    ):
        raise JobStateConflict(
            "The source record changed. Fetch it again before choosing a catalog match."
        )
    if values["choice"] == "link":
        link_duplicate(job, entry, values)
    elif values["choice"] == "cancel":
        job.state, job.finished_at = BackgroundJobState.CANCELLED, timezone.now()
    else:
        restart_source_job(job, entry, values["choice"])
    job.requested_action = RequestedJobAction.NONE
    job.save()
    AuditLog.objects.create(
        actor=actor,
        verb=f"source.resolve.{values['choice']}",
        target_type=job._meta.label_lower,
        target_id=str(job.pk),
    )
    return job
