from dataclasses import replace
from datetime import timedelta

import pytest
from apps.processing.job_models import (
    BackgroundJobKind,
    BackgroundJobState,
    DispatchState,
    JobAttempt,
    JobDispatch,
)
from apps.processing.jobs.attempts import (
    AttemptLost,
    checkpoint_attempt,
    claim_attempt,
    complete_attempt,
)
from apps.processing.jobs.commands import enqueue_job
from apps.processing.jobs.dispatches import (
    claim_dispatches,
    record_dispatch_confirmation,
)
from apps.processing.jobs.recovery import (
    reconcile_missing_dispatches,
    recover_stale_attempts,
    republish_unstarted_jobs,
)
from django.utils import timezone

pytestmark = pytest.mark.django_db


def stale_attempt(command):
    job = enqueue_job(command)
    ownership = claim_attempt(job.dispatches.get().pk)
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        heartbeat_at=timezone.now() - timedelta(minutes=3)
    )
    return job, ownership


def test_recovery_keeps_checkpoints_and_rejects_completion_from_the_old_worker(command):
    job, ownership = stale_attempt(command)
    checkpoint_attempt(ownership, {"resource": 8}, "extracting")
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        heartbeat_at=timezone.now() - timedelta(minutes=3)
    )
    assert recover_stale_attempts(timezone.now() - timedelta(minutes=2)) == 1
    job.refresh_from_db()
    assert job.state == BackgroundJobState.RETRY_WAIT and job.checkpoint == {
        "resource": 8
    }
    assert job.generation == 2 and job.dispatches.count() == 2
    with pytest.raises(AttemptLost):
        complete_attempt(ownership)
    assert recover_stale_attempts(timezone.now() - timedelta(minutes=2)) == 0


def test_a_recent_heartbeat_prevents_recovery(command):
    job, ownership = stale_attempt(command)
    assert checkpoint_attempt(ownership, {}, "extracting")
    assert recover_stale_attempts(timezone.now() - timedelta(minutes=2)) == 0
    job.refresh_from_db()
    assert job.state == BackgroundJobState.RUNNING


def test_interrupted_email_submission_needs_review_without_resending(command):
    job, ownership = stale_attempt(
        replace(command, kind=BackgroundJobKind.DELIVER_KINDLE)
    )
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(stage="sending")
    assert recover_stale_attempts(timezone.now() - timedelta(minutes=2)) == 1
    job.refresh_from_db()
    assert (
        job.state == BackgroundJobState.NEEDS_ATTENTION and job.dispatches.count() == 1
    )
    assert claim_dispatches() == []


def test_reconciliation_repairs_a_missing_dispatch_without_duplicating_it(command):
    job = enqueue_job(command)
    job.generation = 2
    job.save(update_fields=["generation"])
    assert reconcile_missing_dispatches() == 1
    assert reconcile_missing_dispatches() == 0
    assert job.dispatches.count() == 2


def test_unstarted_published_jobs_can_be_republished_but_running_jobs_cannot(command):
    job = enqueue_job(command)
    lease = claim_dispatches()[0]
    assert record_dispatch_confirmation(lease)
    JobDispatch.objects.filter(job=job).update(
        published_at=timezone.now() - timedelta(minutes=6)
    )
    assert republish_unstarted_jobs(timezone.now() - timedelta(minutes=5)) == 1
    assert job.dispatches.get().state == DispatchState.PENDING
    lease = claim_dispatches()[0]
    assert record_dispatch_confirmation(lease)
    assert claim_attempt(lease.identifier) is not None
    JobDispatch.objects.filter(job=job).update(
        published_at=timezone.now() - timedelta(minutes=6)
    )
    assert republish_unstarted_jobs(timezone.now() - timedelta(minutes=5)) == 0
