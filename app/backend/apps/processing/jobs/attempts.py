from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobState,
    JobAttempt,
    JobDispatch,
    RequestedJobAction,
)

from .failure_counts import count_failed_attempts


class AttemptLost(ValueError):
    pass


@dataclass(frozen=True)
class AttemptOwnership:
    job_id: UUID
    attempt_id: UUID
    generation: int


def owned_job(ownership: AttemptOwnership):
    job = BackgroundJob.objects.select_for_update().get(pk=ownership.job_id)
    if (
        job.state != BackgroundJobState.RUNNING
        or job.active_attempt_id != ownership.attempt_id
        or job.generation != ownership.generation
    ):
        raise AttemptLost("This attempt no longer owns the job.")
    return job


def settle_requested_action(job):
    if not job.requested_action:
        return False
    job.state = (
        BackgroundJobState.CANCELLED
        if job.requested_action == RequestedJobAction.CANCEL
        else BackgroundJobState.PAUSED
    )
    job.requested_action = RequestedJobAction.NONE
    job.finished_at = (
        timezone.now() if job.state == BackgroundJobState.CANCELLED else None
    )
    job.active_attempt = None
    job.save()
    return True


def activate_attempt(job):
    attempt = JobAttempt.objects.create(
        job=job,
        number=job.attempt_count + 1,
        generation=job.generation,
        heartbeat_at=timezone.now(),
    )
    job.active_attempt = attempt
    job.attempt_count = attempt.number
    job.state = BackgroundJobState.RUNNING
    job.error_code = ""
    job.save()
    return AttemptOwnership(job.pk, attempt.pk, job.generation)


def dispatch_can_start(job, dispatch):
    return (
        dispatch.generation == job.generation
        and job.state in {BackgroundJobState.QUEUED, BackgroundJobState.RETRY_WAIT}
        and job.available_at <= timezone.now()
    )


@transaction.atomic
def claim_attempt(dispatch_id: UUID):
    dispatch = JobDispatch.objects.get(pk=dispatch_id)
    job = BackgroundJob.objects.select_for_update().get(pk=dispatch.job_id)
    if not dispatch_can_start(job, dispatch) or settle_requested_action(job):
        return None
    if count_failed_attempts(job) >= job.max_attempts:
        job.state = BackgroundJobState.FAILED
        job.error_code = "attempt_limit"
        job.finished_at = timezone.now()
        job.save()
        return None
    return activate_attempt(job)


@transaction.atomic
def checkpoint_attempt(ownership: AttemptOwnership, checkpoint: dict, stage: str):
    job = owned_job(ownership)
    if len(stage) > 64:
        raise ValueError("The execution stage is too long.")
    job.checkpoint = checkpoint
    job.save(update_fields=["checkpoint", "updated_at"])
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        heartbeat_at=timezone.now(), stage=stage
    )
    stopped = settle_requested_action(job)
    if stopped:
        JobAttempt.objects.filter(pk=ownership.attempt_id).update(
            finished_at=timezone.now()
        )
    return not stopped


@transaction.atomic
def complete_attempt(ownership: AttemptOwnership):
    job = owned_job(ownership)
    # Completion records work already performed, including a late stop request.
    job.state = BackgroundJobState.SUCCEEDED
    job.requested_action = RequestedJobAction.NONE
    job.active_attempt = None
    job.finished_at = timezone.now()
    job.save()
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        finished_at=job.finished_at
    )
    return job
