from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, PermissionDenied

from apps.access.models import PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset
from apps.common.permissions import user_has_scope
from apps.processing.job_models import (
    SOURCE_ACTIVE_STATES,
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
    asset = locked_preparation_asset(command.asset_id)
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


def locked_preparation_asset(identifier):
    snapshot = get_object_or_404(GeneratedAsset.objects.only("book_id"), pk=identifier)
    get_object_or_404(
        Book.objects.select_for_update(), pk=snapshot.book_id, deleted_at__isnull=True
    )
    asset = get_object_or_404(
        GeneratedAsset.objects.select_for_update(),
        pk=identifier,
        book_id=snapshot.book_id,
    )
    if BackgroundJob.objects.filter(
        book_id=asset.book_id,
        kind=BackgroundJobKind.PROCESS_SOURCE,
        state__in=SOURCE_ACTIVE_STATES,
    ).exists():
        raise JobStateConflict(
            "Finish or cancel source processing before preparing these files."
        )
    return asset


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
