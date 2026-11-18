"""Tests for Central Job Engine: Engine API Endpoints.

Verifies that the Engine exposes API endpoints for inspecting worker
status, job status, queue depth, and manual reassignment.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestEngineAPI:
    """Engine inspection and management API."""

    def test_list_workers(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        from apps.ingestion.engine.api import list_workers
        workers = list_workers()

        assert len(workers) >= 1
        matching = [w for w in workers if w["hostname"] == worker.hostname]
        assert len(matching) == 1, f"Worker {worker.hostname} should be in list"
        assert matching[0]["status"] == WORKER_STATUS_IDLE

    def test_list_workers_with_status_filter(self, engine, docker_redis_client):
        idle_worker = FakeWorker(docker_redis_client, hostname="idle-api@test")
        busy_worker = FakeWorker(docker_redis_client, hostname="busy-api@test")
        idle_worker.register()
        assert wait_for_redis_key(docker_redis_client, idle_worker.worker_key())

        busy_worker.register()
        assert wait_for_redis_key(docker_redis_client, busy_worker.worker_key())

        # Wait for engine to process registration, then manually override status
        time.sleep(0.3)
        docker_redis_client.hset(busy_worker.worker_key(), "status", WORKER_STATUS_PROCESSING)
        docker_redis_client.hset(busy_worker.worker_key(), "current_job", "some-job")

        from apps.ingestion.engine.api import list_workers
        idle_workers = list_workers(status=WORKER_STATUS_IDLE)
        assert any(w["hostname"] == idle_worker.hostname for w in idle_workers)
        assert not any(w["hostname"] == busy_worker.hostname for w in idle_workers)

        processing_workers = list_workers(status=WORKER_STATUS_PROCESSING)
        assert any(w["hostname"] == busy_worker.hostname for w in processing_workers)

    def test_get_job_status(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "api-job-status-001"
        publish_job_request(docker_redis_client, job_id)
        time.sleep(0.3)

        from apps.ingestion.engine.api import get_job_status
        status = get_job_status(job_id)

        assert status is not None, "Job status should exist"
        assert status["job_id"] == job_id
        assert status["worker_hostname"] == worker.hostname
        assert status["status"] == WORKER_STATUS_PROCESSING

    def test_get_job_status_not_found(self, engine, docker_redis_client):
        from apps.ingestion.engine.api import get_job_status
        status = get_job_status("nonexistent-job")
        assert status is None, "Nonexistent job should return None"

    def test_get_job_status_not_active(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "api-job-completed-001"
        publish_job_request(docker_redis_client, job_id)
        time.sleep(0.3)

        worker.complete_job(job_id)
        time.sleep(0.3)

        from apps.ingestion.engine.api import get_job_status
        status = get_job_status(job_id)
        assert status is None or status.get("status") != WORKER_STATUS_PROCESSING, \
            "Completed job should not show as processing"

    def test_queue_depth(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        from apps.ingestion.engine.api import get_queue_depth
        depth = get_queue_depth()
        assert depth == 0, f"Expected empty queue, got {depth}"

        for i in range(5):
            publish_job_request(docker_redis_client, f"api-depth-{i:03d}")

        time.sleep(0.3)

        depth = get_queue_depth()
        assert depth == 4, f"Expected queue depth 4, got {depth}"

    def test_worker_detail(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, capabilities=["process_submission", "curation"])
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        from apps.ingestion.engine.api import get_worker_detail
        detail = get_worker_detail(worker.hostname)

        assert detail is not None
        assert detail["hostname"] == worker.hostname
        assert detail["status"] == WORKER_STATUS_IDLE
        assert "process_submission" in detail["capabilities"]
        assert "curation" in detail["capabilities"]

    def test_worker_detail_not_found(self, engine, docker_redis_client):
        from apps.ingestion.engine.api import get_worker_detail
        detail = get_worker_detail("nonexistent-worker@test")
        assert detail is None, "Nonexistent worker should return None"

    def test_manual_reassign_job(self, engine, docker_redis_client):
        worker_a = FakeWorker(docker_redis_client, hostname="api-reassign-a@test")
        worker_b = FakeWorker(docker_redis_client, hostname="api-reassign-b@test")
        worker_a.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker_a.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        job_id = "api-reassign-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker_a.hostname, timeout=3.0,
        )

        worker_b.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker_b.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        from apps.ingestion.engine.api import reassign_job
        result = reassign_job(job_id, worker_b.hostname)
        assert result is True, "Reassignment should succeed"
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, worker_b.hostname, timeout=3.0,
        )

    def test_engine_status(self, engine, docker_redis_client):
        from apps.ingestion.engine.api import get_engine_status
        status = get_engine_status()

        assert status is not None
        assert "running" in status
        assert status["running"] is True
        assert "worker_count" in status
        assert "queue_depth" in status
        assert "active_jobs" in status
