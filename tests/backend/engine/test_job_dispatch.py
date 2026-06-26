"""Tests for Central Job Engine: Job Dispatch Logic.

Verifies that the Engine correctly dispatches jobs to idle workers,
queues jobs when all workers are busy, and maintains FIFO ordering.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestJobDispatch:
    """Core dispatch logic — assigning jobs to workers."""

    def test_job_request_with_idle_worker_assigned_immediately(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "dispatch-test-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker.hostname, timeout=3.0,
        )
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_PROCESSING)

    def test_job_request_with_all_busy_worker_is_queued(self, engine, docker_redis_client):
        single_worker = FakeWorker(docker_redis_client)
        single_worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, single_worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        first_job_id = "dispatch-test-101"
        publish_job_request(docker_redis_client, first_job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, first_job_id, single_worker.hostname, timeout=3.0,
        )

        second_job_id = "dispatch-test-102"
        publish_job_request(docker_redis_client, second_job_id)
        assert wait_for_queue_length(docker_redis_client, 1, timeout=3.0)
        assert_job_not_active(docker_redis_client, second_job_id)

    def test_worker_freed_next_queued_job_assigned(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        first_job_id = "dispatch-test-201"
        publish_job_request(docker_redis_client, first_job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, first_job_id, worker.hostname, timeout=3.0,
        )

        second_job_id = "dispatch-test-202"
        publish_job_request(docker_redis_client, second_job_id)
        assert wait_for_queue_length(docker_redis_client, 1, timeout=3.0)
        assert_job_not_active(docker_redis_client, second_job_id)

        worker.complete_job(first_job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, second_job_id, worker.hostname, timeout=3.0,
        )
        assert wait_for_queue_length(docker_redis_client, 0, timeout=3.0)

    def test_fifo_ordering(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_ids = [f"fifo-job-{i:03d}" for i in range(5)]

        first_job = job_ids[0]
        publish_job_request(docker_redis_client, first_job)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, first_job, worker.hostname, timeout=3.0,
        )

        for jid in job_ids[1:]:
            publish_job_request(docker_redis_client, jid)

        for jid in job_ids[1:]:
            wait_for_condition(lambda: docker_redis_client.hget(ACTIVE_JOBS, jid) is None, timeout=3.0)

        assert wait_for_queue_length(docker_redis_client, 4, timeout=3.0)
        queue = docker_redis_client.lrange(PENDING_QUEUE, 0, -1)
        assert queue == job_ids[1:], f"Queue should maintain FIFO order: {queue}"

    def test_no_double_assignment(self, engine, docker_redis_client):
        worker1 = FakeWorker(docker_redis_client, hostname="worker-double-1@test")
        worker2 = FakeWorker(docker_redis_client, hostname="worker-double-2@test")
        worker1.register()
        worker2.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker1.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker2.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "no-double-001"
        publish_job_request(docker_redis_client, job_id)

        assert wait_for_condition(
            lambda: (a := docker_redis_client.hget(ACTIVE_JOBS, job_id)) in (worker1.hostname, worker2.hostname),
            timeout=3.0,
        ), f"Job should be assigned to worker1 or worker2"

        assigned_worker = docker_redis_client.hget(ACTIVE_JOBS, job_id)
        active_count = 0
        for w in [worker1, worker2]:
            if docker_redis_client.hget(w.worker_key(), "current_job") == job_id:
                active_count += 1
        assert active_count == 1, "Job should be assigned to exactly one worker"

    def test_worker_with_matching_capabilities_gets_job(self, engine, docker_redis_client):
        catalog_worker = FakeWorker(
            docker_redis_client,
            hostname="catalog-worker@test",
            capabilities=["catalog_sync"],
        )
        process_worker = FakeWorker(
            docker_redis_client,
            hostname="process-worker@test",
            capabilities=["process_submission"],
        )
        catalog_worker.register()
        process_worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, catalog_worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )
        assert wait_for_redis_hash_field_value(
            docker_redis_client, process_worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        publish_job_request(
            docker_redis_client,
            "capability-test-001",
            job_type="process",
            handler="catalog_sync",
        )
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, "capability-test-001", catalog_worker.hostname, timeout=3.0,
        )
        assert_worker_status(docker_redis_client, process_worker.hostname, WORKER_STATUS_IDLE)

    def test_job_with_no_matching_worker_remains_pending(self, engine, docker_redis_client):
        worker = FakeWorker(
            docker_redis_client,
            capabilities=["process_submission"],
        )
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        publish_job_request(
            docker_redis_client,
            "no-capability-001",
            job_type="process",
            handler="unknown_handler",
        )
        assert wait_for_queue_length(docker_redis_client, 1, timeout=3.0), "Job should stay queued"
        assert_job_not_active(docker_redis_client, "no-capability-001")

    def test_queued_job_retains_handler(self, engine, docker_redis_client, captured_events):
        # 1. Register a worker that can handle "pipeline" jobs
        busy_worker = FakeWorker(docker_redis_client, capabilities=["pipeline"])
        busy_worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, busy_worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )
        
        # 2. Make the worker busy by assigning a dummy job to it
        docker_redis_client.hset(ACTIVE_JOBS, "dummy-job-id", busy_worker.hostname)
        docker_redis_client.hset(busy_worker.worker_key(), "status", WORKER_STATUS_PROCESSING)
        docker_redis_client.hset(busy_worker.worker_key(), "current_job", "dummy-job-id")
        
        # 3. Publish a job request requiring the "pipeline" handler
        job_id = "pipeline-job-001"
        publish_job_request(docker_redis_client, job_id, job_type="pipeline", handler="pipeline")
        
        # Since worker is busy, the job must be queued
        assert wait_for_queue_length(docker_redis_client, 1, timeout=3.0)
        
        # 4. Free the worker by completing its dummy job
        busy_worker.complete_job("dummy-job-id")
        
        # Trigger the engine check (wait for it to dispatch)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, busy_worker.hostname, timeout=3.0,
        )
        
        # 5. Check the captured CH_JOB_ASSIGNED event
        time.sleep(0.2)
        assigned_events = [e for e in captured_events if e["channel"] == CH_JOB_ASSIGNED]
        assert len(assigned_events) > 0, "No CH_JOB_ASSIGNED event was published"
        
        our_event = next((e for e in assigned_events if e["data"].get("job_id") == job_id), None)
        assert our_event is not None, f"No CH_JOB_ASSIGNED event was published for {job_id}"
        event_data = our_event["data"]
        assert event_data.get("worker_hostname") == busy_worker.hostname
        assert event_data.get("handler") == "pipeline"
