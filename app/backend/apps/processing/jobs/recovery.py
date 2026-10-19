from datetime import datetime

from django.db import transaction
from django.db.models import Exists, F, OuterRef
from django.utils import timezone

from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
    DispatchState,
    JobAttempt,
    JobDispatch,
)
from apps.processing.jobs.attempts import AttemptOwnership
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt

from .source_admission import fence_source_dispatch

RECOVERY_BATCH_SIZE = 50


@transaction.atomic
def recover_stale_attempts(cutoff: datetime):
    jobs = (
        BackgroundJob.objects.select_for_update(skip_locked=True, of=("self",))
        .filter(
            state=BackgroundJobState.RUNNING,
            active_attempt__heartbeat_at__lte=cutoff,
        )
        .select_related("active_attempt")
        .order_by("id")[:RECOVERY_BATCH_SIZE]
    )
    recovered = 0
    for job in jobs:
        attempt = job.active_attempt
        if attempt is None:
            raise ValueError("A running job must have an execution attempt.")
        # A heartbeat may commit after the candidate query's snapshot.
        attempt = JobAttempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.heartbeat_at > cutoff:
            continue
        uncertain = (
            job.kind
            in {BackgroundJobKind.DELIVER_KINDLE, BackgroundJobKind.ACCOUNT_MAIL}
            and attempt.stage == "sending"
        )
        failure = AttemptFailure(
            FailureKind.UNCERTAIN if uncertain else FailureKind.TRANSIENT,
            "worker_interrupted",
        )
        fail_attempt(AttemptOwnership(job.pk, attempt.pk, job.generation), failure)
        recovered += 1
    return recovered


@transaction.atomic
def reconcile_missing_dispatches():
    dispatches = JobDispatch.objects.filter(
        job_id=OuterRef("pk"), generation=OuterRef("generation")
    )
    jobs = (
        BackgroundJob.objects.annotate(has_dispatch=Exists(dispatches))
        .select_for_update(skip_locked=True)
        .filter(
            has_dispatch=False,
            state__in=[BackgroundJobState.QUEUED, BackgroundJobState.RETRY_WAIT],
        )
        .order_by("id")[:RECOVERY_BATCH_SIZE]
    )
    reconciled = 0
    for job in jobs:
        JobDispatch.objects.create(
            job=job, generation=job.generation, available_at=job.available_at
        )
        reconciled += 1
    return reconciled


@transaction.atomic
def republish_unstarted_jobs(cutoff: datetime):
    records = (
        JobDispatch.objects.select_for_update(skip_locked=True, of=("self",))
        .filter(
            state=DispatchState.PUBLISHED,
            published_at__lte=cutoff,
            generation=F("job__generation"),
            job__state__in=[BackgroundJobState.QUEUED, BackgroundJobState.RETRY_WAIT],
            job__available_at__lte=timezone.now(),
        )
        .order_by("id")[:RECOVERY_BATCH_SIZE]
    )
    dispatches = list(records.select_related("job"))
    fenced = sum(
        fence_source_dispatch(dispatch.job_id)
        for dispatch in dispatches
        if dispatch.job.kind == "process_source"
    )
    identifiers = [
        dispatch.pk for dispatch in dispatches if dispatch.job.kind != "process_source"
    ]
    return fenced + JobDispatch.objects.filter(pk__in=identifiers).update(
        state=DispatchState.PENDING, available_at=timezone.now(), published_at=None
    )
