"""Tests for Central Job Engine: Job Processing Lifecycle.

Verifies that the Engine correctly tracks job status transitions,
handles completion and failure, and manages worker capacity.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestJobCompletion:
    """Jobs must complete successfully and update state."""

    def test_job_completion_updates_worker_and_active_jobs(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "complete-test-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_PROCESSING)

        worker.complete_job(job_id)
        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) is None,
            timeout=3.0,
        )
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)
        assert_worker_field(docker_redis_client, worker.hostname, "current_job", "")

    def test_job_completion_frees_worker_for_next_job(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job1 = "complete-multi-001"
        job2 = "complete-multi-002"
        publish_job_request(docker_redis_client, job1)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job1, worker.hostname, timeout=3.0,
        )
        publish_job_request(docker_redis_client, job2)
        assert wait_for_queue_length(docker_redis_client, 1, timeout=3.0)

        worker.complete_job(job1)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job2, worker.hostname, timeout=3.0,
        )
        assert wait_for_queue_length(docker_redis_client, 0, timeout=3.0)

    def test_completion_event_published(self, engine, docker_redis_client, captured_events):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "complete-event-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

        worker.complete_job(job_id)
        time.sleep(0.5)

        assert_event(captured_events, CH_JOB_COMPLETED, job_id=job_id, status="succeeded")


class TestJobFailure:
    """Jobs that fail must be handled gracefully."""

    def test_job_failure_marks_worker_idle(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "fail-test-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

        worker.fail_job(job_id, error_message="something went wrong")
        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) is None,
            timeout=3.0,
        )
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)
        assert_worker_field(docker_redis_client, worker.hostname, "current_job", "")

    def test_job_failure_does_not_consume_next_queued_job(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job1 = "fail-multi-001"
        job2 = "fail-multi-002"
        publish_job_request(docker_redis_client, job1)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job1, worker.hostname, timeout=3.0,
        )
        publish_job_request(docker_redis_client, job2)
        assert wait_for_queue_length(docker_redis_client, 1, timeout=3.0)

        worker.fail_job(job1)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job2, worker.hostname, timeout=3.0,
        )
        assert wait_for_queue_length(docker_redis_client, 0, timeout=3.0)

    def test_failure_event_includes_error(self, engine, docker_redis_client, captured_events):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "fail-event-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

        worker.fail_job(job_id, error_message="timeout exceeded")
        time.sleep(0.5)

        assert_event(
            captured_events, CH_JOB_COMPLETED,
            job_id=job_id, status="failed", error_message="timeout exceeded",
        )


class TestWorkerJobTransfer:
    """When a worker completes or fails, its next job is dispatched."""

    def test_worker_does_one_job_then_next_in_queue(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        ids = [f"transfer-{i:03d}" for i in range(4)]
        first = ids[0]
        publish_job_request(docker_redis_client, first)
        for jid in ids[1:]:
            publish_job_request(docker_redis_client, jid)

        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, first, worker.hostname, timeout=3.0,
        )
        assert wait_for_queue_length(docker_redis_client, 3, timeout=3.0)

        for jid in ids:
            assert wait_for_redis_hash_field_value(
                docker_redis_client, ACTIVE_JOBS, jid, worker.hostname, timeout=3.0,
            ), f"Job {jid} should be active for worker before completion"
            worker.complete_job(jid)
            time.sleep(0.3)

        assert wait_for_queue_length(docker_redis_client, 0, timeout=3.0)
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)

    def test_worker_one_by_one_through_queue(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        ids = [f"serial-{i:03d}" for i in range(4)]
        for jid in ids:
            publish_job_request(docker_redis_client, jid)

        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, ids[0], worker.hostname, timeout=3.0,
        )
        assert wait_for_queue_length(docker_redis_client, 3, timeout=3.0)

        for i, jid in enumerate(ids):
            assert wait_for_redis_hash_field_value(
                docker_redis_client, ACTIVE_JOBS, jid, worker.hostname, timeout=3.0,
            ), f"Job {jid} should be active for worker before completion"
            worker.complete_job(jid)
            time.sleep(0.3)

        assert wait_for_queue_length(docker_redis_client, 0, timeout=3.0)
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)

    def test_job_completed_twice_is_idempotent(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "idempotent-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )

        worker.complete_job(job_id)
        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) is None,
            timeout=3.0,
        )

        worker.complete_job(job_id)
        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) is None,
            timeout=3.0,
        ), "Double complete should not error"
