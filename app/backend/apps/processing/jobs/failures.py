import re
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from django.db import transaction
from django.utils import timezone

from apps.processing.job_models import (
    BackgroundJobState,
    JobAttempt,
    JobDispatch,
    RequestedJobAction,
)
from apps.processing.jobs.attempts import (
    AttemptOwnership,
    owned_job,
    settle_requested_action,
)

from .failure_counts import count_failed_attempts
from .source_defects import record_source_defect
from .source_recovery import (
    SOURCE_AVAILABILITY_ERRORS,
    rebase_changed_source,
    schedule_source_availability,
)

MAX_RETRY_DELAY_SECONDS = 300
INITIAL_RETRY_DELAY_SECONDS = 15
SOURCE_RECHECK_INTERVAL = timedelta(hours=6)


class FailureKind(StrEnum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class AttemptFailure:
    kind: FailureKind
    code: str


def schedule_retry(job, failure_count):
    delay = min(
        INITIAL_RETRY_DELAY_SECONDS * 2 ** min(failure_count - 1, 5),
        MAX_RETRY_DELAY_SECONDS,
    )
    job.state = BackgroundJobState.RETRY_WAIT
    job.generation += 1
    job.available_at = timezone.now() + timedelta(seconds=delay)
    job.finished_at = None
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )


def schedule_source_recheck(job):
    job.state, job.finished_at = BackgroundJobState.RETRY_WAIT, None
    job.generation += 1
    job.available_at = timezone.now() + SOURCE_RECHECK_INTERVAL
    job.checkpoint = {
        key: value
        for key, value in job.checkpoint.items()
        if key
        in {"source_revision", "source_url", "catalog_revision", "catalog_book_id"}
    }
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )


@transaction.atomic
def fail_attempt(ownership: AttemptOwnership, failure: AttemptFailure):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", failure.code):
        raise ValueError("Job failures need a bounded, non-sensitive error code.")
    job = owned_job(ownership)
    record_source_defect(job, failure)
    job.error_code = failure.code
    job.active_attempt = None
    job.finished_at = timezone.now()
    job.state = (
        BackgroundJobState.NEEDS_ATTENTION
        if failure.kind == FailureKind.UNCERTAIN
        else BackgroundJobState.FAILED
    )
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        finished_at=job.finished_at, error_code=failure.code
    )
    if failure.kind != FailureKind.UNCERTAIN and settle_requested_action(job):
        return job
    if failure.kind != FailureKind.UNCERTAIN:
        job.requested_action = RequestedJobAction.NONE
    failure_count = count_failed_attempts(job)
    if job.kind == "process_source" and failure.code == "source_content_unavailable":
        schedule_source_recheck(job)
    elif (
        job.kind == "process_source"
        and failure.kind == FailureKind.TRANSIENT
        and failure.code in SOURCE_AVAILABILITY_ERRORS
    ):
        schedule_source_availability(job)
    elif job.kind == "process_source" and failure.code == "source_record_changed":
        rebase_changed_source(job)
    elif failure.kind == FailureKind.TRANSIENT and failure_count < job.max_attempts:
        schedule_retry(job, failure_count)
    job.save()
    return job
