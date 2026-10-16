from datetime import UTC

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.processing.job_models import BackgroundJob, BackgroundJobKind, JobDispatch
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .policy import require_source_url, source_hosts
from .queries import linked_source_book


def matching_source_command(actor, identifier, values):
    existing = BackgroundJob.objects.filter(pk=identifier).first()
    if existing is None:
        return None
    if (
        existing.requested_by_id != actor.pk
        or existing.kind != BackgroundJobKind.PROCESS_SOURCE
        or existing.input.get("command") != values
    ):
        raise JobStateConflict("This operation identifier belongs to another request.")
    return existing


def source_command_values(entry, expected):
    if entry.updated_at != expected:
        raise JobStateConflict("The source record changed. Refresh before processing.")
    if linked_source_book(entry) is not None:
        raise JobStateConflict("This source already links to a catalog book.")
    try:
        url = require_source_url(entry.source_url, source_hosts())
        if normalize_source_url(url) != url:
            raise ValueError("Use the canonical source record URL.")
    except (ExecutionFailure, ValueError):
        raise ValidationError(
            {"source": "Configure an allowed canonical book source before processing."}
        ) from None
    return {
        "source_id": str(entry.pk),
        "source_revision": expected.astimezone(UTC).isoformat(),
        "source_url": url,
    }


@transaction.atomic
def persist_source_job(actor, identifier, entry):
    job = BackgroundJob.objects.create(
        id=identifier,
        requested_by=actor,
        source_record=entry,
        kind=BackgroundJobKind.PROCESS_SOURCE,
        input={"command": source_command_values(entry, entry.updated_at)},
        available_at=timezone.now(),
    )
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    return job


@transaction.atomic
def request_source_processing(actor, identifiers, expected):
    operation_id, source_id = identifiers
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    entry = get_object_or_404(
        SourceCatalogEntry.objects.select_for_update(), pk=source_id
    )
    values = {
        "source_id": str(entry.pk),
        "source_revision": expected.astimezone(UTC).isoformat(),
        "source_url": entry.source_url,
    }
    existing = matching_source_command(actor, operation_id, values)
    if existing is not None:
        return existing
    source_command_values(entry, expected)
    try:
        return persist_source_job(actor, operation_id, entry)
    except IntegrityError as error:
        existing = matching_source_command(actor, operation_id, values)
        if existing is not None:
            return existing
        raise JobStateConflict(
            "A source operation is already active. Inspect its result before another request."
        ) from error
