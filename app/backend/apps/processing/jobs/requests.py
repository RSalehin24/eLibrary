from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, PermissionDenied

from apps.access.models import PermissionScope
from apps.accounts.models import User
from apps.catalog.models import GeneratedAsset
from apps.common.permissions import user_has_scope
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    RequestedJobAction,
)
from apps.processing.jobs.commands import JobCommand, JobConflict, enqueue_job
from apps.processing.jobs.controls import request_stop, resume_job


class JobStateConflict(APIException):
    status_code = 409
    default_code = "state_conflict"
    default_detail = "The operation changed. Refresh its status before continuing."


def require_processing_manager(user):
    if not user.is_active or not user_has_scope(
        user, [PermissionScope.PROCESSING_MANAGE]
    ):
        raise PermissionDenied("Processing management access is required.")


@dataclass(frozen=True)
class PreparationRequest:
    identifier: UUID
    asset_id: UUID
    expected_updated_at: datetime


@transaction.atomic
def request_preparation(actor: User, command: PreparationRequest):
    actor = User.objects.select_for_update().get(pk=actor.pk)
    require_processing_manager(actor)
    asset = get_object_or_404(
        GeneratedAsset.objects.select_for_update().filter(
            book__deleted_at__isnull=True
        ),
        pk=command.asset_id,
    )
    if asset.updated_at != command.expected_updated_at:
        raise JobStateConflict(
            "The asset changed. Refresh its information before preparing it."
        )
    values = {"asset_revision": asset.updated_at.isoformat()}
    try:
        return enqueue_job(
            JobCommand(
                command.identifier, actor, asset, BackgroundJobKind.PREPARE_EPUB, values
            )
        )
    except JobConflict as error:
        raise JobStateConflict(str(error)) from error


@dataclass(frozen=True)
class JobControlRequest:
    identifier: UUID
    expected_updated_at: datetime
    action: str


@transaction.atomic
def control_background_job(actor: User, command: JobControlRequest):
    actor = User.objects.select_for_update().get(pk=actor.pk)
    require_processing_manager(actor)
    job = get_object_or_404(
        BackgroundJob.objects.select_for_update().exclude(
            kind=BackgroundJobKind.ACCOUNT_MAIL
        ),
        pk=command.identifier,
    )
    if job.updated_at != command.expected_updated_at:
        raise JobStateConflict()
    try:
        if command.action == "resume":
            return resume_job(job.pk)
        return request_stop(job.pk, RequestedJobAction(command.action))
    except (JobConflict, ValueError) as error:
        raise JobStateConflict(str(error)) from error
