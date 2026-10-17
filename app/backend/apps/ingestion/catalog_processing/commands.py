from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.ingestion.source_discovery.configuration import discovery_configuration
from apps.processing.job_models import BackgroundJob, BackgroundJobKind, JobDispatch
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .queries import eligible_catalog_entries


def matching_catalog_command(actor, identifier, command):
    job = BackgroundJob.objects.filter(pk=identifier).first()
    if job is None:
        return None
    if (
        job.requested_by_id != actor.pk
        or job.kind != BackgroundJobKind.PROCESS_CATALOG
        or job.input.get("command") != command
    ):
        raise JobStateConflict("This operation identifier belongs to another command.")
    return job


@transaction.atomic
def create_catalog_job(actor, values, run):
    job = BackgroundJob.objects.create(
        id=values["operation_id"],
        requested_by=actor,
        kind=BackgroundJobKind.PROCESS_CATALOG,
        input={"command": values["command"]},
        available_at=timezone.now(),
        automation_run=run,
    )
    total = eligible_catalog_entries().filter(created_at__lte=job.created_at).count()
    job.checkpoint = {"bulk_total": total, "bulk_queued": 0, "bulk_rejected": 0}
    job.save(update_fields=["checkpoint", "updated_at"])
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    return job


@transaction.atomic
def request_catalog_processing(actor, values, run=None):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    revision = discovery_configuration()["configuration_revision"]
    if values["configuration_revision"] != revision:
        raise JobStateConflict(
            "The source configuration changed. Refresh before processing."
        )
    command = {"configuration_revision": revision}
    existing = matching_catalog_command(actor, values["operation_id"], command)
    if existing is not None:
        return existing
    try:
        return create_catalog_job(
            actor, {"operation_id": values["operation_id"], "command": command}, run
        )
    except IntegrityError as error:
        existing = matching_catalog_command(actor, values["operation_id"], command)
        if existing is not None:
            return existing
        raise JobStateConflict(
            "A Process All operation is already active. Open its progress before starting another."
        ) from error
