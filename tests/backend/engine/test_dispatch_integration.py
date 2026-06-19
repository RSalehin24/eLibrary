"""Tests for Central Job Engine: End-to-End Dispatch Integration.

Verifies the full flow: Django creates a ProcessingJob → publishes job
request via Redis → Engine receives → assigns to worker → worker completes
→ Engine updates state → Django model reflects completion.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *

DB_TRANSACTION = pytest.mark.django_db(transaction=True)


class TestDispatchIntegration:
    """Full end-to-end integration tests.

    Uses transaction=True so the engine thread running in background
    can see DB records created by the test thread.
    """

    @DB_TRANSACTION
    def test_job_created_in_db_dispatch_to_worker(self, engine, docker_redis_client, jobs_in_db):
        job = jobs_in_db(job_type="reprocess", status="queued")
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        publish_job_request(docker_redis_client, str(job.id), job_type="reprocess", handler="process_submission")
        time.sleep(0.3)

        assert_job_active(docker_redis_client, str(job.id), worker.hostname)

        job.refresh_from_db()
        assert job.worker_hostname == worker.hostname, \
            f"Expected worker_hostname '{worker.hostname}', got '{job.worker_hostname}'"

    @DB_TRANSACTION
    def test_job_completed_updates_db(self, engine, docker_redis_client, jobs_in_db):
        job = jobs_in_db(job_type="reprocess", status="queued")
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        publish_job_request(docker_redis_client, str(job.id), job_type="reprocess", handler="process_submission")
        time.sleep(0.3)
        assert_job_active(docker_redis_client, str(job.id), worker.hostname)

        worker.complete_job(str(job.id))
        time.sleep(0.3)

        job.refresh_from_db()
        assert job.status == "succeeded", \
            f"Expected job status 'succeeded', got '{job.status}'"
        assert job.finished_at is not None, "finished_at should be set"

    @DB_TRANSACTION
    def test_job_failed_updates_db(self, engine, docker_redis_client, jobs_in_db):
        job = jobs_in_db(job_type="reprocess", status="queued")
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        publish_job_request(docker_redis_client, str(job.id), job_type="reprocess", handler="process_submission")
        time.sleep(0.3)
        assert_job_active(docker_redis_client, str(job.id), worker.hostname)

        worker.fail_job(str(job.id), error_message="processing error")
        time.sleep(0.3)

        job.refresh_from_db()
        assert job.status == "failed", \
            f"Expected job status 'failed', got '{job.status}'"
        assert job.last_error == "processing error", \
            f"Expected last_error 'processing error', got '{job.last_error}'"

    @DB_TRANSACTION
    def test_full_lifecycle_multiple_jobs(self, engine, docker_redis_client, jobs_in_db):
        jobs = jobs_in_db(3, job_type="reprocess", status="queued")
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        for j in jobs:
            publish_job_request(docker_redis_client, str(j.id), job_type="reprocess", handler="process_submission")
        time.sleep(0.3)

        for i, j in enumerate(jobs):
            if i == 0:
                assert_job_active(docker_redis_client, str(j.id), worker.hostname)
            else:
                assert_job_not_active(docker_redis_client, str(j.id))

        for j in jobs:
            assert wait_for_redis_hash_field_value(
                docker_redis_client, ACTIVE_JOBS, str(j.id), worker.hostname, timeout=3.0,
            ), f"Job {j.id} should be active for worker before completion"
            worker.complete_job(str(j.id))
            time.sleep(0.2)

            j.refresh_from_db()
            assert j.status == "succeeded", f"Job {j.id} should be 'succeeded', got '{j.status}'"

        assert wait_for_queue_length(docker_redis_client, 0)

    @DB_TRANSACTION
    def test_dispatch_from_django_to_redis_no_celery(self, engine, docker_redis_client, jobs_in_db):
        """Simulate what Django would do: save job, publish to Redis."""
        job = jobs_in_db(job_type="reprocess", status="queued")
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        from apps.ingestion.engine.dispatch import dispatch_job
        dispatch_job(str(job.id), job_type="reprocess", handler="process_submission")

        time.sleep(0.3)
        assert_job_active(docker_redis_client, str(job.id), worker.hostname)

    @DB_TRANSACTION
    def test_stale_worker_job_reassignment_updates_db(self, engine_with_heartbeat_check, docker_redis_client, jobs_in_db):
        stale_worker = FakeWorker(docker_redis_client, hostname="stale-int-worker@test")
        healthy_worker = FakeWorker(docker_redis_client, hostname="healthy-int-worker@test")

        stale_worker.register()
        assert wait_for_redis_key(docker_redis_client, stale_worker.worker_key())

        job = jobs_in_db(job_type="reprocess", status="queued")
        publish_job_request(docker_redis_client, str(job.id), job_type="reprocess", handler="process_submission")
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, str(job.id), stale_worker.hostname, timeout=3.0,
        )

        healthy_worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, healthy_worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        stale_worker.heartbeat()

        # Keep healthy_worker alive while stale_worker goes stale
        wait_start = time.time()
        while time.time() - wait_start < HEARTBEAT_TIMEOUT_SECONDS + 5:
            if docker_redis_client.hget(stale_worker.worker_key(), "status") == WORKER_STATUS_STALE:
                break
            healthy_worker.heartbeat()
            time.sleep(2)

        assert docker_redis_client.hget(stale_worker.worker_key(), "status") == WORKER_STATUS_STALE

        actual_owner = docker_redis_client.hget(ACTIVE_JOBS, str(job.id))
        assert actual_owner == healthy_worker.hostname, \
            f"Job {job.id} should be reassigned to healthy worker (owner={actual_owner})"

        job.refresh_from_db()
        assert job.worker_hostname == healthy_worker.hostname, \
            f"Job should be reassigned to healthy worker, got '{job.worker_hostname}'"
