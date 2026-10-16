from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.catalog.models import GeneratedAsset
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
    DispatchState,
    JobAttempt,
    JobDispatch,
    RequestedJobAction,
)
from apps.processing.jobs.attempts import (
    AttemptLost,
    checkpoint_attempt,
    claim_attempt,
    complete_attempt,
)
from apps.processing.jobs.commands import JobConflict, enqueue_job
from apps.processing.jobs.controls import request_stop, resume_job
from apps.processing.jobs.dispatches import (
    claim_dispatches,
    record_dispatch_confirmation,
    record_dispatch_failure,
)
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from django.db import IntegrityError, transaction
from django.utils import timezone

pytestmark = pytest.mark.django_db


def claimed_job(command):
    job = enqueue_job(command)
    return job, claim_attempt(job.dispatches.get().pk)


def test_job_and_dispatch_are_atomic_and_the_command_is_idempotent(
    command, monkeypatch
):
    job = enqueue_job(command)
    assert enqueue_job(command).pk == job.pk
    assert BackgroundJob.objects.count() == JobDispatch.objects.count() == 1
    original = JobDispatch.objects.create

    def fail_dispatch(**values):
        raise RuntimeError("simulated database interruption")

    monkeypatch.setattr(JobDispatch.objects, "create", fail_dispatch)
    with pytest.raises(RuntimeError):
        enqueue_job(replace(command, identifier=uuid4()))
    monkeypatch.setattr(JobDispatch.objects, "create", original)
    assert BackgroundJob.objects.count() == JobDispatch.objects.count() == 1


@pytest.mark.parametrize("difference", ["actor", "values", "kind"])
def test_reused_command_identifiers_cannot_change_the_operation(command, difference):
    enqueue_job(command)
    changes = {
        "actor": User.objects.create_user(email="other-job@library.test"),
        "values": {"changed": True},
        "kind": BackgroundJobKind.DELIVER_KINDLE,
    }
    with pytest.raises(JobConflict):
        enqueue_job(replace(command, **{difference: changes[difference]}))
    assert BackgroundJob.objects.count() == 1


@pytest.mark.parametrize("change", [{"status": "failed"}, {"asset_type": "html"}])
def test_enqueue_rechecks_the_asset_after_it_was_loaded(command, change):
    GeneratedAsset.objects.filter(pk=command.asset.pk).update(**change)
    with pytest.raises(JobConflict):
        enqueue_job(command)
    assert not BackgroundJob.objects.exists() and not JobDispatch.objects.exists()


def test_duplicate_delivery_and_stale_completion_cannot_run_the_job_twice(command):
    job, ownership = claimed_job(command)
    assert ownership is not None
    assert claim_attempt(job.dispatches.get().pk) is None
    assert checkpoint_attempt(ownership, {"resource": 2}, "extracting")
    completed = complete_attempt(ownership)
    assert completed.state == BackgroundJobState.SUCCEEDED
    with pytest.raises(AttemptLost):
        complete_attempt(ownership)
    assert job.attempts.count() == 1


@pytest.mark.parametrize(
    "action", [RequestedJobAction.PAUSE, RequestedJobAction.CANCEL]
)
def test_stop_requests_remain_requests_until_the_worker_reaches_a_checkpoint(
    command, action
):
    job, ownership = claimed_job(command)
    requested = request_stop(job.pk, action)
    assert (
        requested.state == BackgroundJobState.RUNNING
        and requested.requested_action == action
    )
    assert not checkpoint_attempt(ownership, {"resource": 3}, "extracting")
    job.refresh_from_db()
    assert job.state == (
        BackgroundJobState.PAUSED
        if action == RequestedJobAction.PAUSE
        else BackgroundJobState.CANCELLED
    )
    assert not job.requested_action and job.active_attempt_id is None
    assert JobAttempt.objects.get(pk=ownership.attempt_id).finished_at


def test_pauses_do_not_consume_the_bounded_failure_retry_budget(command):
    job, ownership = claimed_job(command)
    for _ in range(4):
        request_stop(job.pk, RequestedJobAction.PAUSE)
        assert not checkpoint_attempt(ownership, {"resource": 4}, "extracting")
        job = resume_job(job.pk)
        assert claim_attempt(job.dispatches.order_by("generation").first().pk) is None
        ownership = claim_attempt(job.dispatches.get(generation=job.generation).pk)
        assert ownership is not None
    assert complete_attempt(ownership).state == BackgroundJobState.SUCCEEDED
    assert job.attempts.count() == 5


def test_only_transient_failures_retry_with_backoff_and_a_new_dispatch(command):
    job, ownership = claimed_job(command)
    failed = fail_attempt(
        ownership, AttemptFailure(FailureKind.TRANSIENT, "source_timeout")
    )
    assert failed.state == BackgroundJobState.RETRY_WAIT and failed.generation == 2
    assert failed.available_at > timezone.now() + timedelta(seconds=10)
    assert failed.dispatches.count() == 2
    assert claim_attempt(failed.dispatches.get(generation=2).pk) is None
    with pytest.raises(AttemptLost):
        complete_attempt(ownership)
    BackgroundJob.objects.filter(pk=job.pk).update(available_at=timezone.now())
    assert claim_attempt(failed.dispatches.get(generation=2).pk) is not None


@pytest.mark.parametrize(
    "failure,state",
    [
        (FailureKind.PERMANENT, BackgroundJobState.FAILED),
        (FailureKind.UNCERTAIN, BackgroundJobState.NEEDS_ATTENTION),
    ],
)
def test_permanent_and_uncertain_side_effects_are_not_retried(command, failure, state):
    job, ownership = claimed_job(command)
    result = fail_attempt(ownership, AttemptFailure(failure, "delivery_result_unknown"))
    assert result.state == state and result.dispatches.count() == 1
    assert claim_dispatches() == []
    with pytest.raises(JobConflict):
        resume_job(job.pk)


def test_a_failed_unit_honors_an_already_requested_pause(command):
    job, ownership = claimed_job(command)
    request_stop(job.pk, RequestedJobAction.PAUSE)
    result = fail_attempt(
        ownership, AttemptFailure(FailureKind.TRANSIENT, "source_timeout")
    )
    assert result.state == BackgroundJobState.PAUSED and result.dispatches.count() == 1


def test_retry_budget_finishes_after_three_failed_attempts(command):
    job = enqueue_job(command)
    for _ in range(3):
        BackgroundJob.objects.filter(pk=job.pk).update(available_at=timezone.now())
        job.refresh_from_db()
        ownership = claim_attempt(job.dispatches.get(generation=job.generation).pk)
        assert ownership is not None
        job = fail_attempt(
            ownership, AttemptFailure(FailureKind.TRANSIENT, "source_timeout")
        )
    assert job.state == BackgroundJobState.FAILED and job.attempts.count() == 3
    assert job.dispatches.count() == 3


def test_dispatch_leases_recover_uncertain_publication_without_stale_confirmation(
    command,
):
    job = enqueue_job(command)
    first = claim_dispatches()[0]
    assert claim_dispatches() == []
    JobDispatch.objects.filter(job=job).update(
        lease_expires_at=timezone.now() - timedelta(seconds=1)
    )
    second = claim_dispatches()[0]
    assert first.owner != second.owner
    assert not record_dispatch_confirmation(first)
    assert record_dispatch_confirmation(second)
    assert job.dispatches.get().state == DispatchState.PUBLISHED
    assert claim_dispatches() == []


def test_failed_dispatches_back_off_without_changing_job_state(command):
    job = enqueue_job(command)
    lease = claim_dispatches()[0]
    assert record_dispatch_failure(lease)
    dispatch = job.dispatches.get()
    assert dispatch.state == DispatchState.PENDING and dispatch.failure_count == 1
    assert dispatch.available_at > timezone.now()
    assert claim_dispatches() == []
    job.refresh_from_db()
    assert job.state == BackgroundJobState.QUEUED


def test_database_rejects_duplicate_dispatches_and_attempt_numbers(command):
    job, _ownership = claimed_job(command)
    with pytest.raises(IntegrityError), transaction.atomic():
        JobDispatch.objects.create(job=job, generation=1, available_at=timezone.now())
    with pytest.raises(IntegrityError), transaction.atomic():
        JobAttempt.objects.create(
            job=job, number=1, generation=1, heartbeat_at=timezone.now()
        )


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_dispatch_batch_is_bounded(limit):
    with pytest.raises(ValueError):
        claim_dispatches(limit)
