"""Tests for Central Job Engine: Concurrent Operations.

Verifies that the Engine handles multiple workers processing jobs
concurrently without race conditions or double-assignment.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestConcurrentOperations:
    """Multiple workers operating simultaneously."""

    def test_two_workers_two_jobs(self, engine, docker_redis_client):
        w1 = FakeWorker(docker_redis_client, hostname="con-w1@test")
        w2 = FakeWorker(docker_redis_client, hostname="con-w2@test")
        w1.register()
        w2.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, w1.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )
        assert wait_for_redis_hash_field_value(
            docker_redis_client, w2.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        publish_job_request(docker_redis_client, "con-2w-001")
        publish_job_request(docker_redis_client, "con-2w-002")

        assert wait_for_condition(
            lambda: {docker_redis_client.hget(ACTIVE_JOBS, "con-2w-001"),
                     docker_redis_client.hget(ACTIVE_JOBS, "con-2w-002")} == {w1.hostname, w2.hostname},
            timeout=3.0,
        ), "Both workers should have jobs"

    def test_simultaneous_registrations(self, engine, docker_redis_client):
        workers_list = []
        for i in range(10):
            w = FakeWorker(docker_redis_client, hostname=f"con-reg-{i}@test")
            w.register()
            workers_list.append(w)

        time.sleep(0.3)

        for w in workers_list:
            assert docker_redis_client.exists(w.worker_key()), \
                f"Worker {w.hostname} should be registered"

    def test_no_double_assign_concurrent_completion(self, engine, docker_redis_client):
        w1 = FakeWorker(docker_redis_client, hostname="con-double-w1@test")
        w2 = FakeWorker(docker_redis_client, hostname="con-double-w2@test")
        w1.register()
        w2.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, w1.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )
        assert wait_for_redis_hash_field_value(
            docker_redis_client, w2.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "con-double-001"
        publish_job_request(docker_redis_client, job_id)

        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) is not None,
            timeout=3.0,
        )
        owner = docker_redis_client.hget(ACTIVE_JOBS, job_id)

        worker_a = w1 if owner == w1.hostname else w2
        worker_b = w2 if worker_a == w1 else w1

        worker_a.complete_job(job_id)
        time.sleep(0.1)
        worker_b.complete_job(job_id)
        time.sleep(0.2)

        assert_job_not_active(docker_redis_client, job_id)

    def test_concurrent_job_processing_all_complete(self, engine, docker_redis_client):
        workers_list = []
        for i in range(3):
            w = FakeWorker(docker_redis_client, hostname=f"con-all-{i}@test")
            w.register()
            assert wait_for_redis_hash_field_value(
                docker_redis_client, w.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
            )
            workers_list.append(w)

        job_count = 9
        for i in range(job_count):
            publish_job_request(docker_redis_client, f"con-all-{i:03d}")

        assert wait_for_queue_length(docker_redis_client, 6, timeout=5.0)
        active_count = docker_redis_client.hlen(ACTIVE_JOBS)
        assert active_count == 3, f"Expected 3 active jobs, got {active_count}"

        # Process all jobs
        for i in range(9):
            job_id = f"con-all-{i:03d}"
            assigned = docker_redis_client.hget(ACTIVE_JOBS, job_id)
            if assigned:
                matching = [w for w in workers_list if w.hostname == assigned][0]
                matching.complete_job(job_id)
                time.sleep(0.1)

        assert wait_for_queue_length(docker_redis_client, 0, timeout=5.0)
        assert docker_redis_client.hlen(ACTIVE_JOBS) == 0, "All jobs should be complete"

    def test_concurrent_same_worker_multiple_jobs(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, hostname="con-single@test")
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        for i in range(4):
            publish_job_request(docker_redis_client, f"con-single-{i:03d}")

        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, "con-single-000", worker.hostname, timeout=3.0,
        )
        assert wait_for_queue_length(docker_redis_client, 3, timeout=3.0)

        worker.complete_job("con-single-000")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, "con-single-001", worker.hostname, timeout=3.0,
        )
        assert wait_for_queue_length(docker_redis_client, 2, timeout=3.0)

    def test_rapid_job_requests_no_loss(self, engine, docker_redis_client):
        workers_list = []
        for i in range(2):
            w = FakeWorker(docker_redis_client, hostname=f"con-rapid-{i}@test")
            w.register()
            assert wait_for_redis_key(docker_redis_client, w.worker_key())
            workers_list.append(w)

        for i in range(10):
            publish_job_request(docker_redis_client, f"con-rapid-{i:03d}")

        assert wait_for_queue_length(docker_redis_client, 8, timeout=5.0), \
            "Queue should have 8 jobs (10 total - 2 active)"
        active_count = docker_redis_client.hlen(ACTIVE_JOBS)
        queue_length = docker_redis_client.llen(PENDING_QUEUE)
        total = active_count + queue_length
        assert total == 10, f"Expected 10 total jobs (active+queue), got {total}"
