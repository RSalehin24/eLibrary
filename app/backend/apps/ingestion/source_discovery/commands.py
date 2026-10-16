from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.processing.job_models import BackgroundJob, BackgroundJobKind, JobDispatch
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .configuration import discovery_configuration


def existing_discovery_command(actor, identifier, command):
    job = BackgroundJob.objects.filter(pk=identifier).first()
    if job is None:
        return None
    if (
        job.requested_by_id != actor.pk
        or job.kind != BackgroundJobKind.DISCOVER_SOURCE
        or job.input.get("command") != command
    ):
        raise JobStateConflict(
            "This operation identifier belongs to a different command."
        )
    return job


@transaction.atomic
def create_discovery_job(actor, identifier, command):
    job = BackgroundJob.objects.create(
        id=identifier,
        requested_by=actor,
        kind=BackgroundJobKind.DISCOVER_SOURCE,
        input={"command": command},
        available_at=timezone.now(),
    )
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    return job


@transaction.atomic
def request_source_discovery(actor, values):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    configured = discovery_configuration()
    command = {**configured, "max_pages": values["max_pages"]}
    if values["configuration_revision"] != configured["configuration_revision"]:
        raise JobStateConflict(
            "The configured source changed. Inspect its current address before discovery."
        )
    identifier = values["operation_id"]
    existing = existing_discovery_command(actor, identifier, command)
    if existing is not None:
        return existing
    try:
        return create_discovery_job(actor, identifier, command)
    except IntegrityError as error:
        existing = existing_discovery_command(actor, identifier, command)
        if existing is not None:
            return existing
        raise JobStateConflict(
            "A discovery operation is already active. Inspect it before another request."
        ) from error
