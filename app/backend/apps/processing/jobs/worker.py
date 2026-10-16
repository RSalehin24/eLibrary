import logging
from uuid import UUID

from celery.exceptions import SoftTimeLimitExceeded
from django.db import DatabaseError

from apps.accounts.link_mail.worker import run_account_mail
from apps.delivery.worker import run_kindle_delivery
from apps.ingestion.source_discovery.worker import run_source_discovery
from apps.ingestion.source_processing.worker import run_source_processing
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    JobAttempt,
    JobDispatch,
)
from apps.processing.jobs.attempts import AttemptLost, claim_attempt, complete_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from apps.processing.jobs.heartbeat import maintain_heartbeat
from apps.processing.jobs.preparation import run_preparation

logger = logging.getLogger(__name__)


def execute_claimed_job(ownership):
    job = BackgroundJob.objects.get(pk=ownership.job_id)
    if job.kind == BackgroundJobKind.PREPARE_EPUB:
        return run_preparation(ownership)
    if job.kind == BackgroundJobKind.DELIVER_KINDLE:
        return run_kindle_delivery(ownership)
    if job.kind == BackgroundJobKind.ACCOUNT_MAIL:
        return run_account_mail(ownership)
    if job.kind == BackgroundJobKind.PROCESS_SOURCE:
        return run_source_processing(ownership)
    if job.kind == BackgroundJobKind.DISCOVER_SOURCE:
        return run_source_discovery(ownership)
    raise ExecutionFailure(FailureKind.PERMANENT, "unsupported_job_kind")


def execute_with_heartbeat(ownership, heartbeat):
    with heartbeat(ownership):
        completed = execute_claimed_job(ownership)
    if completed:
        complete_attempt(ownership)


def record_execution_failure(ownership, failure):
    try:
        fail_attempt(ownership, failure)
    except AttemptLost:
        logger.info(
            "Stale background job outcome ignored.",
            extra={"job_id": str(ownership.job_id)},
        )


def interrupted_execution_failure(ownership):
    attempt = JobAttempt.objects.select_related("job").get(pk=ownership.attempt_id)
    if (
        attempt.job.kind
        in {BackgroundJobKind.DELIVER_KINDLE, BackgroundJobKind.ACCOUNT_MAIL}
        and attempt.stage == "sending"
    ):
        return AttemptFailure(FailureKind.UNCERTAIN, "mail_acceptance_unknown")
    return AttemptFailure(FailureKind.TRANSIENT, "execution_interrupted")


def unexpected_execution_failure(ownership):
    failure = interrupted_execution_failure(ownership)
    return (
        failure
        if failure.kind == FailureKind.UNCERTAIN
        else AttemptFailure(FailureKind.PERMANENT, "processing_internal_error")
    )


def run_background_job(dispatch_id: UUID, heartbeat=maintain_heartbeat):
    try:
        ownership = claim_attempt(dispatch_id)
    except JobDispatch.DoesNotExist:
        logger.warning(
            "Unknown background job dispatch ignored.",
            extra={"dispatch_id": str(dispatch_id)},
        )
        return
    if ownership is None:
        return
    try:
        execute_with_heartbeat(ownership, heartbeat)
    except AttemptLost:
        logger.info(
            "Background job attempt ownership lost.",
            extra={"job_id": str(ownership.job_id)},
        )
    except ExecutionFailure as error:
        record_execution_failure(ownership, error.failure)
    except (DatabaseError, SoftTimeLimitExceeded):
        record_execution_failure(ownership, interrupted_execution_failure(ownership))
    except Exception:
        logger.exception(
            "Background processing failed.", extra={"job_id": str(ownership.job_id)}
        )
        record_execution_failure(
            ownership,
            unexpected_execution_failure(ownership),
        )
