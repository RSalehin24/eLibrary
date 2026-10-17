from uuid import uuid5

from django.db import transaction
from django.http import Http404
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.ingestion.source_processing.commands import request_source_processing
from apps.processing.jobs.attempts import AttemptLost, checkpoint_attempt, owned_job

from .queries import current_catalog_job, eligible_catalog_entries

CATALOG_BATCH_SIZE = 50
MAX_RECORDED_REJECTIONS = 20


def next_catalog_batch(job):
    if job.checkpoint.get("bulk_pending"):
        return job.checkpoint["bulk_pending"]
    entries = eligible_catalog_entries().filter(created_at__lte=job.created_at)
    if job.checkpoint.get("bulk_cursor"):
        entries = entries.filter(pk__gt=job.checkpoint["bulk_cursor"])
    return [
        {"id": str(entry.pk), "revision": entry.updated_at.isoformat()}
        for entry in entries.order_by("id").only("id", "updated_at")[
            :CATALOG_BATCH_SIZE
        ]
    ]


@transaction.atomic
def queue_catalog_child(ownership, selection):
    snapshot = current_catalog_job(ownership.job_id)
    User.objects.select_for_update(no_key=True).get(pk=snapshot.requested_by_id)
    parent = owned_job(ownership)
    current_catalog_job(parent.pk)
    if not checkpoint_attempt(ownership, parent.checkpoint, "queueing_catalog_books"):
        raise AttemptLost("Catalog queueing stopped.")
    child = request_source_processing(
        snapshot.requested_by,
        (uuid5(parent.pk, selection["id"]), selection["id"]),
        parse_datetime(selection["revision"]),
    )
    child.parent_job = parent
    child.automation_run = parent.automation_run
    child.save(update_fields=["parent_job", "automation_run", "updated_at"])
    return child


def catalog_child_outcome(ownership, selection):
    try:
        queue_catalog_child(ownership, selection)
    except Http404:
        return "source_record_missing"
    except APIException as error:
        return error.default_code
    return ""


def save_catalog_outcome(ownership, selection, error_code):
    job = current_catalog_job(ownership.job_id)
    checkpoint = dict(job.checkpoint)
    counter = "bulk_rejected" if error_code else "bulk_queued"
    checkpoint[counter] = checkpoint.get(counter, 0) + 1
    checkpoint["bulk_pending"] = checkpoint["bulk_pending"][1:]
    checkpoint["bulk_cursor"] = selection["id"]
    if error_code:
        checkpoint["bulk_errors"] = [
            *checkpoint.get("bulk_errors", []),
            {"source_id": selection["id"], "code": error_code},
        ][-MAX_RECORDED_REJECTIONS:]
    return checkpoint_attempt(ownership, checkpoint, "queueing_catalog_books")


def run_catalog_processing(ownership):
    while True:
        job = current_catalog_job(ownership.job_id)
        selections = next_catalog_batch(job)
        checkpoint = {**job.checkpoint, "bulk_pending": selections}
        if not checkpoint_attempt(ownership, checkpoint, "queueing_catalog_books"):
            return False
        if not selections:
            return checkpoint_attempt(ownership, checkpoint, "catalog_books_queued")
        for selection in selections:
            error_code = catalog_child_outcome(ownership, selection)
            if not save_catalog_outcome(ownership, selection, error_code):
                return False
