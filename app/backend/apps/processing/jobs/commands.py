from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType
from apps.processing.job_models import BackgroundJob, BackgroundJobKind, JobDispatch


class JobConflict(ValueError):
    pass


@dataclass(frozen=True)
class JobCommand:
    identifier: UUID
    actor: User
    asset: GeneratedAsset
    kind: BackgroundJobKind
    values: dict[str, Any] = field(default_factory=dict)


def matching_job(job, command):
    return (
        job.requested_by_id == command.actor.pk
        and job.asset_id == command.asset.pk
        and job.kind == command.kind
        and job.input == command.values
    )


@transaction.atomic
def enqueue_job(command: JobCommand):
    # Serialize commands while allowing unrelated foreign-key references.
    User.objects.select_for_update(no_key=True).get(pk=command.actor.pk)
    existing = BackgroundJob.objects.filter(pk=command.identifier).first()
    if existing is not None:
        if not matching_job(existing, command):
            raise JobConflict("This command identifier belongs to another request.")
        return existing
    try:
        return create_job(command)
    except IntegrityError as error:
        existing = BackgroundJob.objects.filter(pk=command.identifier).first()
        if existing is None:
            raise
        if not matching_job(existing, command):
            raise JobConflict(
                "This command identifier belongs to another request."
            ) from error
        return existing


@transaction.atomic
def create_job(command: JobCommand):
    asset = GeneratedAsset.objects.select_for_update().get(pk=command.asset.pk)
    if command.kind not in {
        BackgroundJobKind.PREPARE_EPUB,
        BackgroundJobKind.DELIVER_KINDLE,
    }:
        raise JobConflict("Unknown background operation.")
    if (
        asset.asset_type != GeneratedAssetType.EPUB
        or asset.status != GeneratedAssetStatus.READY
    ):
        raise JobConflict("This operation needs a ready EPUB asset.")
    job = BackgroundJob.objects.create(
        id=command.identifier,
        requested_by=command.actor,
        book_id=asset.book_id,
        asset=asset,
        kind=command.kind,
        input=command.values,
        available_at=timezone.now(),
    )
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    return job
