from apps.delivery.checkpoints import record_mail_acceptance
from apps.delivery.job_data import (
    delivery_job,
    delivery_recipients,
    pending_recipient_indices,
    require_delivery_asset,
    require_delivery_permission,
)
from apps.delivery.mail_transport import (
    KindleMessage,
    SMTPKindleMailer,
    connected_mailer,
    validate_message,
)
from apps.delivery.payload import load_kindle_payload
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def delivery_payload(job):
    payload = load_kindle_payload(job.asset)
    previous = job.checkpoint.get("checksum") or job.asset.checksum
    if previous and previous != payload.checksum:
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_changed")
    return payload


def prepare_recipient_message(ownership, payload, index):
    job = delivery_job(ownership.job_id)
    recipient = delivery_recipients(job)[index]
    require_delivery_asset(job)
    require_delivery_permission(job, recipient)
    message = KindleMessage(
        job.input["subject"],
        job.input["sender"],
        recipient,
        payload.filename,
        payload.content,
    )
    validate_message(message)
    return job, message


def deliver_recipient(ownership, shipment, mailer):
    job, message, index = shipment
    checkpoint = {**job.checkpoint, "sending_index": index}
    if not checkpoint_attempt(ownership, checkpoint, "sending"):
        return False
    try:
        mailer.send(message)
    except ExecutionFailure as error:
        if error.failure.kind != FailureKind.UNCERTAIN:
            rejected = {
                **checkpoint,
                "rejected_index": index,
                "rejection_code": error.failure.code,
            }
            rejected.pop("sending_index", None)
            checkpoint_attempt(ownership, rejected, "rejected")
        raise
    return record_mail_acceptance(ownership, job.requested_by_id, index)


def prepare_delivery(ownership, job, first_index):
    require_delivery_asset(job)
    require_delivery_permission(job, delivery_recipients(job)[first_index])
    if not checkpoint_attempt(ownership, job.checkpoint, "loading_asset"):
        return None
    payload = delivery_payload(job)
    job, _message = prepare_recipient_message(ownership, payload, first_index)
    checkpoint = {**job.checkpoint, "checksum": payload.checksum}
    if not checkpoint_attempt(ownership, checkpoint, "connecting"):
        return None
    return payload


def deliver_pending(ownership, payload, mailer):
    job = delivery_job(ownership.job_id)
    for index in pending_recipient_indices(job):
        current, message = prepare_recipient_message(ownership, payload, index)
        if not deliver_recipient(ownership, (current, message, index), mailer):
            return False
    return True


def run_kindle_delivery(ownership, mailer_factory=SMTPKindleMailer):
    job = delivery_job(ownership.job_id)
    pending = pending_recipient_indices(job)
    if not pending:
        return True
    payload = prepare_delivery(ownership, job, pending[0])
    if payload is None:
        return False
    with connected_mailer(mailer_factory(), job.pk) as mailer:
        return deliver_pending(ownership, payload, mailer)
