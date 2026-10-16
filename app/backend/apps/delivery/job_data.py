from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from apps.accounts.kindle import MAX_KINDLE_RECIPIENTS, normalize_kindle_addresses
from apps.accounts.mail_configuration import kindle_sender_email
from apps.catalog.models import GeneratedAssetStatus, GeneratedAssetType
from apps.common.permissions import user_can_send_to_kindle
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def delivery_job(identifier):
    return BackgroundJob.objects.select_related(
        "requested_by", "asset", "asset__book", "book"
    ).get(pk=identifier)


def delivery_recipients(job):
    recipients = job.input.get("recipients")
    if (
        not isinstance(recipients, list)
        or not 1 <= len(recipients) <= MAX_KINDLE_RECIPIENTS
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "delivery_input_invalid")
    try:
        normalized = normalize_kindle_addresses(recipients)
        validate_email(job.input.get("sender", ""))
    except ValidationError:
        raise ExecutionFailure(
            FailureKind.PERMANENT, "delivery_input_invalid"
        ) from None
    if normalized != recipients or not isinstance(job.input.get("subject"), str):
        raise ExecutionFailure(FailureKind.PERMANENT, "delivery_input_invalid")
    return recipients


def require_delivery_asset(job):
    asset = job.asset
    if (
        job.book is None
        or asset is None
        or job.book.deleted_at
        or asset.book_id != job.book_id
        or asset.asset_type != GeneratedAssetType.EPUB
        or asset.status != GeneratedAssetStatus.READY
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_unavailable")
    if job.input.get("asset_revision") != asset.updated_at.isoformat():
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_changed")
    if job.input["sender"] != kindle_sender_email():
        raise ExecutionFailure(FailureKind.PERMANENT, "sender_configuration_changed")


def require_delivery_permission(job, recipient):
    actor = job.requested_by
    if (
        actor is None
        or not actor.is_active
        or not user_can_send_to_kindle(actor, job.book)
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "permission_revoked")
    try:
        configured = normalize_kindle_addresses(actor.kindle_emails) or []
    except ValidationError:
        raise ExecutionFailure(
            FailureKind.PERMANENT, "recipient_configuration_invalid"
        ) from None
    if recipient not in configured:
        raise ExecutionFailure(FailureKind.PERMANENT, "recipient_removed")


def accepted_recipient_indices(job):
    accepted = job.checkpoint.get("accepted", [])
    count = len(delivery_recipients(job))
    if not isinstance(accepted, list) or any(
        type(index) is not int or not 0 <= index < count for index in accepted
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "checkpoint_invalid")
    return set(accepted)


def pending_recipient_indices(job):
    accepted = accepted_recipient_indices(job)
    return [
        index for index in range(len(delivery_recipients(job))) if index not in accepted
    ]
