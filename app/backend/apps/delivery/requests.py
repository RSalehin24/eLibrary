from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.kindle import MAX_KINDLE_RECIPIENTS, normalize_kindle_addresses
from apps.accounts.mail_configuration import kindle_sender_email
from apps.accounts.models import User
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import (
    Book,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.common.permissions import user_can_send_to_kindle
from apps.delivery.mail_transport import checked_mail_parameters
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    RequestedJobAction,
)
from apps.processing.jobs.commands import JobCommand, JobConflict, enqueue_job
from apps.processing.jobs.controls import request_stop
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.requests import JobStateConflict


def kindle_book(actor, slug):
    book = catalog_object_by_slug(Book.objects.filter(deleted_at__isnull=True), slug)
    if not actor.is_active or not user_can_send_to_kindle(actor, book):
        raise PermissionDenied(
            "Kindle permission or ownership is required for this book."
        )
    return book


def ready_kindle_asset(book):
    asset = book.generated_assets.filter(
        asset_type=GeneratedAssetType.EPUB, status=GeneratedAssetStatus.READY
    ).first()
    if asset is None:
        raise JobStateConflict("This book does not have a ready EPUB asset.")
    return asset


def configured_recipients(actor):
    try:
        return normalize_kindle_addresses(actor.kindle_emails) or []
    except DjangoValidationError as error:
        raise ValidationError({"recipients": list(error.messages)}) from error


def kindle_mail_configured():
    try:
        checked_mail_parameters()
        validate_email(kindle_sender_email())
    except (ExecutionFailure, DjangoValidationError):
        return False
    return True


@dataclass(frozen=True)
class KindleRequest:
    identifier: UUID
    expected_updated_at: datetime
    recipients: tuple[str, ...]


def kindle_request_values(actor, asset, selected):
    configured = configured_recipients(actor)
    recipients = normalize_kindle_addresses(selected) or []
    if not 1 <= len(recipients) <= MAX_KINDLE_RECIPIENTS or any(
        recipient not in configured for recipient in recipients
    ):
        raise ValidationError(
            {"recipients": "Select addresses currently configured in your profile."}
        )
    return {
        "asset_revision": asset.updated_at.isoformat(),
        "recipients": recipients,
        "sender": kindle_sender_email(),
        "subject": asset.book.title,
    }


@transaction.atomic
def request_kindle_delivery(actor, slug, command: KindleRequest):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    book = kindle_book(actor, slug)
    asset = get_object_or_404(
        GeneratedAsset.objects.select_for_update(of=("self",)).select_related("book"),
        book=book,
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
    )
    if asset.updated_at != command.expected_updated_at:
        raise JobStateConflict("The book asset changed. Refresh before sending it.")
    if not kindle_mail_configured():
        raise JobStateConflict("Kindle delivery is not configured yet.")
    values = kindle_request_values(actor, asset, command.recipients)
    try:
        return enqueue_job(
            JobCommand(
                command.identifier,
                actor,
                asset,
                BackgroundJobKind.DELIVER_KINDLE,
                values,
            )
        )
    except JobConflict as error:
        raise JobStateConflict(str(error)) from error


def own_deliveries(actor):
    return BackgroundJob.objects.filter(
        requested_by=actor, kind=BackgroundJobKind.DELIVER_KINDLE
    ).select_related("book")


@transaction.atomic
def cancel_kindle_delivery(actor, identifier, expected_updated_at):
    User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    job = get_object_or_404(
        own_deliveries(actor).select_for_update(of=("self",)), pk=identifier
    )
    if job.updated_at != expected_updated_at:
        raise JobStateConflict()
    try:
        return request_stop(job.pk, RequestedJobAction.CANCEL)
    except JobConflict as error:
        raise JobStateConflict(str(error)) from error
