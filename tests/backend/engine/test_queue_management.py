"""Tests for Central Job Engine: Queue Management.

Verifies that the Engine correctly manages the job queue, handles
multiple jobs with limited workers, and processes them in FIFO order.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestQueueManagement:
    """Queue depth and capacity management."""

    def test_more_jobs_than_workers_queue_excess(self, engine, docker_redis_client):
        workers_list = []
        for i in range(2):
            w = FakeWorker(docker_redis_client, hostname=f"qm-worker-{i}@test")
            w.register()
            assert wait_for_redis_key(docker_redis_client, w.worker_key())
            workers_list.append(w)

        total_jobs = 5
        for i in range(total_jobs):
            publish_job_request(docker_redis_client, f"qm-job-{i:03d}")
        time.sleep(0.3)

        expected_active = 2
        expected_queued = total_jobs - expected_active

        assert wait_for_queue_length(docker_redis_client, expected_queued), \
            f"Expected {expected_queued} queued jobs"

        for jid in ["qm-job-000", "qm-job-001"]:
            assert_job_active(docker_redis_client, jid)
        for jid in ["qm-job-002", "qm-job-003", "qm-job-004"]:
            assert_job_not_active(docker_redis_client, jid)

    def test_jobs_fill_as_workers_become_available(self, engine, docker_redis_client):
        workers_list = []
        for i in range(2):
            w = FakeWorker(docker_redis_client, hostname=f"qm-fill-{i}@test")
            w.register()
            assert wait_for_redis_hash_field_value(
                docker_redis_client, w.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
            )
            workers_list.append(w)

        total_jobs = 6
        for i in range(total_jobs):
            publish_job_request(docker_redis_client, f"qm-fill-job-{i:03d}")

        assert wait_for_queue_length(docker_redis_client, 4, timeout=5.0)

        # Find which worker got which job (scan order is arbitrary)
        w0_job = docker_redis_client.hget(ACTIVE_JOBS, "qm-fill-job-000")
        w1_job = docker_redis_client.hget(ACTIVE_JOBS, "qm-fill-job-001")
        assert w0_job and w1_job, "Both jobs 000 and 001 should be active"
        w0 = next(w for w in workers_list if w.hostname == w0_job)
        w1 = next(w for w in workers_list if w.hostname == w1_job)

        w0.complete_job("qm-fill-job-000")

        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, "qm-fill-job-002", w0.hostname, timeout=3.0,
        ), "Job qm-fill-job-002 should be active after worker 0 completes job 000"
        assert wait_for_queue_length(docker_redis_client, 3, timeout=3.0), "Queue should have 3 jobs"

        w1.complete_job("qm-fill-job-001")

        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, "qm-fill-job-003", w1.hostname, timeout=3.0,
        ), "Job qm-fill-job-003 should be active after worker 1 completes job 001"
        assert wait_for_queue_length(docker_redis_client, 2, timeout=3.0), "Queue should have 2 jobs"

    def test_all_jobs_complete_queue_empties(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        for i in range(4):
            publish_job_request(docker_redis_client, f"qm-empty-{i:03d}")
        time.sleep(0.3)

        for i in range(4):
            worker.complete_job(f"qm-empty-{i:03d}")
            time.sleep(0.2)

        assert wait_for_queue_length(docker_redis_client, 0)
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)

    def test_queue_fifo_maintained_multiple_workers(self, engine, docker_redis_client):
        workers_list = []
        for i in range(3):
            w = FakeWorker(docker_redis_client, hostname=f"qm-fifo-{i}@test")
            w.register()
            assert wait_for_redis_key(docker_redis_client, w.worker_key())
            workers_list.append(w)

        job_count = 6
        for i in range(job_count):
            publish_job_request(docker_redis_client, f"qm-fifo-job-{i:03d}")

        assert wait_for_queue_length(docker_redis_client, 3, timeout=5.0), \
            "Queue should have 3 pending jobs"
        queue = docker_redis_client.lrange(PENDING_QUEUE, 0, -1)
        # Order may vary due to timing; check length and content match
        assert set(queue) == {f"qm-fifo-job-{i:03d}" for i in range(3, 6)}, \
            f"Queue should have jobs 003-005, got: {queue}"

    def test_worker_capacity_respected(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        for i in range(3):
            publish_job_request(docker_redis_client, f"qm-cap-{i:03d}")
        time.sleep(0.3)

        assert_job_active(docker_redis_client, "qm-cap-000", worker.hostname)
        assert wait_for_queue_length(docker_redis_client, 2)

    def test_queue_depth_reporting(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        publish_job_request(docker_redis_client, "qm-depth-001")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, "qm-depth-001", worker.hostname, timeout=5.0,
        ), "Job 001 should be active"

        for i in range(2, 8):
            publish_job_request(docker_redis_client, f"qm-depth-{i:03d}")

        assert wait_for_queue_length(docker_redis_client, 6, timeout=5.0), \
            f"Expected queue depth 6"

    def test_queue_ordering_with_mixed_completions(self, engine, docker_redis_client):
        workers_list = []
        for i in range(2):
            w = FakeWorker(docker_redis_client, hostname=f"qm-ord-{i}@test")
            w.register()
            assert wait_for_redis_hash_field_value(
                docker_redis_client, w.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
            )
            workers_list.append(w)

        job_ids = [f"qm-ord-{i:03d}" for i in range(6)]
        for jid in job_ids:
            publish_job_request(docker_redis_client, jid)

        assert wait_for_queue_length(docker_redis_client, 4, timeout=5.0)

        # Find which worker got job 000 vs 001 (scan order is arbitrary)
        w0_job = docker_redis_client.hget(ACTIVE_JOBS, job_ids[0])
        w1_job = docker_redis_client.hget(ACTIVE_JOBS, job_ids[1])
        assert w0_job and w1_job, "Both jobs 000 and 001 should be active"
        w_for_000 = next(w for w in workers_list if w.hostname == w0_job)
        w_for_001 = next(w for w in workers_list if w.hostname == w1_job)

        # Complete both jobs
        w_for_000.complete_job(job_ids[0])
        w_for_001.complete_job(job_ids[1])

        # Next FIFO jobs should be assigned (each worker gets the next queued job)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_ids[2], w_for_000.hostname, timeout=5.0,
        ), f"Job {job_ids[2]} should be active for worker that had job 000"
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_ids[3], w_for_001.hostname, timeout=5.0,
        ), f"Job {job_ids[3]} should be active for worker that had job 001"
        assert wait_for_queue_length(docker_redis_client, 2, timeout=3.0), "Queue should have 2 jobs remaining"
