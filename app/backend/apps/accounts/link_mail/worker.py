from django.db import transaction
from django.utils import timezone

from apps.access.models import PermissionScope
from apps.accounts.management_access.policy import account_is_editable
from apps.common.permissions import user_has_scope
from apps.delivery.mail_transport import SMTPMailer, connected_mailer, validate_message
from apps.processing.job_models import BackgroundJob, JobAttempt
from apps.processing.jobs.attempts import (
    checkpoint_attempt,
    complete_attempt,
    owned_job,
)
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .commands import link_revision
from .message import account_message


def require_current_request(job):
    target = job.account
    action = job.input["command"]["action"]
    if not target.is_active or link_revision(target) != job.input["link_revision"]:
        raise ExecutionFailure(FailureKind.PERMANENT, "account_link_superseded")
    if action == "reset":
        return
    actor = job.requested_by
    if (
        actor is None
        or not actor.is_active
        or not user_has_scope(actor, [PermissionScope.ACCESS_MANAGE])
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "permission_revoked")
    if not account_is_editable(actor, target) or not target.can_resend_setup_email:
        raise ExecutionFailure(FailureKind.PERMANENT, "account_link_superseded")


@transaction.atomic
def record_acceptance(ownership):
    job = owned_job(ownership)
    job.checkpoint = {"accepted_at": timezone.now().isoformat()}
    job.save(update_fields=["checkpoint", "updated_at"])
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        stage="accepted", heartbeat_at=timezone.now()
    )
    complete_attempt(ownership)


def submit_account_message(ownership, mailer):
    job = BackgroundJob.objects.select_related("account", "requested_by").get(
        pk=ownership.job_id
    )
    require_current_request(job)
    message = account_message(job.account, job.input["command"]["action"])
    validate_message(message)
    if not checkpoint_attempt(ownership, job.checkpoint, "sending"):
        return False
    try:
        mailer.send(message)
    except ExecutionFailure as error:
        if error.failure.kind != FailureKind.UNCERTAIN:
            checkpoint_attempt(
                ownership, {"rejection_code": error.failure.code}, "rejected"
            )
        raise
    record_acceptance(ownership)
    return False


def run_account_mail(ownership, mailer_factory=SMTPMailer):
    job = BackgroundJob.objects.select_related("account", "requested_by").get(
        pk=ownership.job_id
    )
    require_current_request(job)
    validate_message(account_message(job.account, job.input["command"]["action"]))
    if not checkpoint_attempt(ownership, job.checkpoint, "connecting"):
        return False
    with connected_mailer(mailer_factory(), job.pk, "Account") as mailer:
        return submit_account_message(ownership, mailer)
