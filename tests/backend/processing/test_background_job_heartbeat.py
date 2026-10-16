from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from queue import Queue
from threading import Event
from time import monotonic

import pytest
from apps.processing.job_models import BackgroundJob, JobAttempt
from apps.processing.jobs import heartbeat
from apps.processing.jobs.attempts import AttemptLost, claim_attempt
from apps.processing.jobs.commands import enqueue_job
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from apps.processing.jobs.recovery import recover_stale_attempts
from django.db import (
    DatabaseError,
    close_old_connections,
    connection,
    connections,
    transaction,
)
from django.utils import timezone

pytestmark = pytest.mark.django_db(transaction=True)


def ownership_for(command):
    job = enqueue_job(command)
    return claim_attempt(job.dispatches.get().pk)


def test_heartbeat_preserves_the_checkpoint_and_rejects_stale_ownership(command):
    ownership = ownership_for(command)
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        heartbeat_at=timezone.now() - timedelta(minutes=5), stage="preparing"
    )
    heartbeat.heartbeat_attempt(ownership)
    attempt = JobAttempt.objects.get(pk=ownership.attempt_id)
    assert attempt.heartbeat_at > timezone.now() - timedelta(seconds=5)
    assert attempt.stage == "preparing"
    fail_attempt(ownership, AttemptFailure(FailureKind.TRANSIENT, "interrupted"))
    with pytest.raises(AttemptLost):
        heartbeat.heartbeat_attempt(ownership)


def test_heartbeat_commits_on_its_own_connection_during_a_processing_transaction(
    command, monkeypatch
):
    ownership = ownership_for(command)
    observed = Event()
    original = heartbeat.heartbeat_attempt

    def pulse(claim):
        original(claim)
        observed.set()

    monkeypatch.setattr(heartbeat, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(heartbeat, "heartbeat_attempt", pulse)
    with heartbeat.maintain_heartbeat(ownership), transaction.atomic():
        command.asset.__class__.objects.select_for_update().get(pk=command.asset.pk)
        assert observed.wait(timeout=5)
    assert JobAttempt.objects.get(
        pk=ownership.attempt_id
    ).heartbeat_at > timezone.now() - timedelta(seconds=5)


@pytest.mark.parametrize("error_type", [DatabaseError, RuntimeError])
def test_a_heartbeat_failure_reaches_the_worker_boundary(
    command, monkeypatch, error_type
):
    ownership = ownership_for(command)
    interrupted = Event()

    def pulse(_):
        interrupted.set()
        raise error_type("synthetic heartbeat interruption")

    monkeypatch.setattr(heartbeat, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(heartbeat, "heartbeat_attempt", pulse)
    with (
        pytest.raises(ExecutionFailure, match="heartbeat_unavailable"),
        heartbeat.maintain_heartbeat(ownership),
    ):
        assert interrupted.wait(timeout=5)


def recover_on_connection(cutoff, process_id):
    close_old_connections()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            process_id.put(cursor.fetchone()[0])
        return recover_stale_attempts(cutoff)
    finally:
        connections.close_all()


def wait_for_database_lock(process_id):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute("SELECT cardinality(pg_blocking_pids(%s)) > 0", [process_id])
            if cursor.fetchone()[0]:
                return
        Event().wait(0.01)
    raise AssertionError("Recovery did not reach the locked job.")


def test_recovery_rechecks_a_heartbeat_committed_after_its_candidate_snapshot(
    command,
):
    ownership = ownership_for(command)
    cutoff = timezone.now() - timedelta(minutes=2)
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        heartbeat_at=cutoff - timedelta(seconds=1)
    )
    process_id = Queue()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            JobAttempt.objects.select_for_update().get(pk=ownership.attempt_id)
            future = executor.submit(recover_on_connection, cutoff, process_id)
            wait_for_database_lock(process_id.get(timeout=5))
            JobAttempt.objects.filter(pk=ownership.attempt_id).update(
                heartbeat_at=timezone.now()
            )
        assert future.result(timeout=5) == 0
    assert BackgroundJob.objects.get(pk=ownership.job_id).state == "running"
