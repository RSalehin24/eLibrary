from uuid import uuid5

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.catalog.editorial.lifecycle import unfinished_book_work
from apps.catalog.editorial.service import withdraw_book
from apps.ingestion.source_processing.defect_recovery import recover_source_defect
from apps.ingestion.source_processing.issues import available_source_choices
from apps.ingestion.source_processing.recovery import restart_repaired_source
from apps.ingestion.source_processing.regeneration import request_book_regeneration
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.requests import JobStateConflict
from apps.processing.jobs.source_defects import source_defect_waits_for_code

SOURCE_BULK_ACTIONS = ("retry_source", "recreate_source", "archive_book")


def available_source_bulk_actions(job):
    if job.kind != "process_source":
        return []
    actions = []
    if any(
        choice in available_source_choices(job)
        for choice in ("retry", "resume_preparation")
    ):
        actions.append("retry_source")
    if (
        job.book_id
        and getattr(job, "can_edit_book", False)
        and job.book.deleted_at is None
        and not getattr(job, "other_book_work", False)
        and job.state in {"failed", "needs_attention", "succeeded", "cancelled"}
    ):
        if not source_defect_waits_for_code(job):
            actions.append("recreate_source")
        if job.book.state != "archived":
            actions.append("archive_book")
    return actions


def retry_source_job(actor, job):
    if job.checkpoint.get("source_defect"):
        recovered = recover_source_defect(job.pk)
        if recovered is None:
            raise JobStateConflict(
                "The defect is waiting for relevant code or input changes."
            )
        return recovered
    choices = available_source_choices(job)
    choice = next(
        (value for value in ("resume_preparation", "retry") if value in choices), None
    )
    if choice is None:
        raise JobStateConflict("This source job has no safe retry action.")
    if choice == "retry" and job.book_id is None:
        return restart_repaired_source(actor, job.pk)
    return resolve_source_job(
        actor, job.pk, {"choice": choice, "expected_updated_at": job.updated_at}
    )


def settle_source_recovery(actor, job):
    if job.state in {"failed", "needs_attention"}:
        return resolve_source_job(
            actor, job.pk, {"choice": "cancel", "expected_updated_at": job.updated_at}
        )
    if job.state not in {"succeeded", "cancelled"}:
        raise JobStateConflict(
            "Finish or stop current processing before changing the book."
        )
    return job


def checked_book_revision(job, entry):
    if not job.book_id or not entry.get("expected_book_updated_at"):
        raise ValidationError("Book actions require the displayed book revision.")
    if job.book.updated_at != entry["expected_book_updated_at"]:
        raise JobStateConflict("The book changed. Refresh it before continuing.")


@transaction.atomic
def control_source_job(actor, values, action):
    entry, operation_id = values
    job = get_object_or_404(
        BackgroundJob.objects.select_for_update(of=("self",)).select_related(
            "source_record", "book"
        ),
        pk=entry["id"],
        kind="process_source",
    )
    if job.updated_at != entry["expected_updated_at"]:
        raise JobStateConflict()
    if action == "retry_source":
        return retry_source_job(actor, job)
    checked_book_revision(job, entry)
    settle_source_recovery(actor, job)
    if action == "recreate_source":
        if source_defect_waits_for_code(job):
            raise JobStateConflict(
                "Wait for the processing defect to be fixed before recreating this book."
            )
        return request_book_regeneration(
            actor,
            job.book_id,
            {
                "operation_id": uuid5(operation_id, str(job.pk)),
                "expected_updated_at": entry["expected_book_updated_at"],
            },
        )
    if action != "archive_book":
        raise ValidationError("Choose a supported source recovery action.")
    if unfinished_book_work(job.book):
        raise JobStateConflict("Other processing is still active for this book.")
    withdraw_book(actor, job.book_id, entry["expected_book_updated_at"])
    return job
