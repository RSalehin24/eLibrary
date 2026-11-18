"""Tests for Central Job Engine: Worker Lifecycle.

Verifies that workers can register, send heartbeats, and deregister
via Redis Pub/Sub, and that the Engine maintains correct state.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestWorkerRegistration:
    """A worker must register before it can receive jobs."""

    def test_worker_registers_and_appears_in_registry(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, hostname="worker1@test")
        worker.register()

        key = worker.worker_key()
        assert wait_for_redis_key(docker_redis_client, key), "Worker key not created"
        assert_worker_field(docker_redis_client, worker.hostname, "status", WORKER_STATUS_IDLE)
        assert_worker_field(docker_redis_client, worker.hostname, "hostname", worker.hostname)

    def test_worker_with_capabilities(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client, hostname="worker-cap@test",
                            capabilities=["process_submission", "catalog_sync"])
        worker.register()

        key = worker.worker_key()
        assert wait_for_redis_key(docker_redis_client, key)
        caps = docker_redis_client.hget(key, "capabilities")
        assert caps is not None
        caps_parsed = json.loads(caps)
        assert "process_submission" in caps_parsed
        assert "catalog_sync" in caps_parsed

    def test_multiple_workers_can_register(self, engine, docker_redis_client):
        workers_list = []
        for i in range(5):
            w = FakeWorker(docker_redis_client, hostname=f"worker{i}@test")
            w.register()
            workers_list.append(w)

        for w in workers_list:
            assert wait_for_redis_key(docker_redis_client, w.worker_key()), \
                f"Worker {w.hostname} did not register"

    def test_duplicate_hostname_updates_existing(self, engine, docker_redis_client):
        hostname = "dupe@test"
        w1 = FakeWorker(docker_redis_client, hostname=hostname, capabilities=["process_submission"])
        w1.register()
        assert wait_for_redis_key(docker_redis_client, w1.worker_key())

        w2 = FakeWorker(docker_redis_client, hostname=hostname, capabilities=["catalog_sync"])
        w2.register()
        time.sleep(0.2)

        caps = docker_redis_client.hget(w2.worker_key(), "capabilities")
        caps_parsed = json.loads(caps)
        assert caps_parsed == ["catalog_sync"], "Duplicate registration should update capabilities"

    def test_register_sets_timestamp(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()

        key = worker.worker_key()
        assert wait_for_redis_key(docker_redis_client, key)
        registered_at = docker_redis_client.hget(key, "registered_at")
        assert registered_at is not None, "registered_at should be set"
        assert len(registered_at) > 0


class TestWorkerHeartbeat:
    """Workers must periodically push heartbeats to remain alive."""

    def test_heartbeat_updates_timestamp(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        initial_beat = docker_redis_client.hget(worker.worker_key(), "last_heartbeat")
        time.sleep(0.1)

        worker.heartbeat()
        time.sleep(0.1)

        updated_beat = docker_redis_client.hget(worker.worker_key(), "last_heartbeat")
        assert updated_beat != initial_beat, "Heartbeat should update last_heartbeat timestamp"

    def test_idle_worker_heartbeat_maintains_idle_status(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        ), "Worker should be idle after registration"

        for _ in range(3):
            worker.heartbeat()
            assert wait_for_redis_hash_field_value(
                docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=1.0,
            ), "Worker should stay idle after heartbeat"

    def test_worker_stops_heartbeating(self, engine_with_heartbeat_check, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.heartbeat()
        # Do NOT send more heartbeats — wait for stale detection
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_STALE,
            timeout=HEARTBEAT_TIMEOUT_SECONDS + 5,
        ), "Worker should be marked stale after heartbeat timeout"

    def test_worker_resumed_heartbeat_clears_stale(self, engine_with_heartbeat_check, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.heartbeat()
        # Wait for stale
        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_STALE,
            timeout=HEARTBEAT_TIMEOUT_SECONDS + 5,
        )

        worker.heartbeat()
        time.sleep(0.5)
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)


class TestWorkerDeregistration:
    """Workers must deregister cleanly on shutdown."""

    def test_worker_deregisters_and_is_removed(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.deregister()
        assert wait_for_condition(
            lambda: not docker_redis_client.exists(worker.worker_key()),
            timeout=3.0,
        ), "Worker key should be removed after deregistration"

    def test_deregister_idempotent(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.deregister()
        assert wait_for_condition(
            lambda: not docker_redis_client.exists(worker.worker_key()),
            timeout=3.0,
        ), "Worker key should be removed after first deregister"

        worker.deregister()  # Should not raise or error
        assert not docker_redis_client.exists(worker.worker_key())

    def test_deregister_unknown_worker_does_not_error(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.deregister()  # Never registered — should be no-op
        assert True, "Deregistering unregistered worker should not raise"

    def test_deregister_frees_active_jobs(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "test-job-001"
        docker_redis_client.hset(ACTIVE_JOBS, job_id, worker.hostname)
        docker_redis_client.hset(worker.worker_key(), "current_job", job_id)
        docker_redis_client.hset(worker.worker_key(), "status", WORKER_STATUS_PROCESSING)

        worker.deregister()

        # Job should NOT be active anymore — it should be returned to queue
        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) is None,
            timeout=3.0,
        ), f"Job {job_id} should be removed from active after worker deregister"

    def test_deregister_with_current_job_requeues_it(self, engine, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        job_id = "test-job-to-requeue"
        docker_redis_client.hset(ACTIVE_JOBS, job_id, worker.hostname)
        docker_redis_client.hset(worker.worker_key(), "current_job", job_id)
        docker_redis_client.hset(worker.worker_key(), "status", WORKER_STATUS_PROCESSING)

        worker.deregister()

        # Job should be back in pending queue
        assert wait_for_condition(
            lambda: docker_redis_client.lpos(PENDING_QUEUE, job_id) is not None,
            timeout=3.0,
        ), f"Job {job_id} should be requeued"
