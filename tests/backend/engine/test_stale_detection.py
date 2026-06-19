"""Tests for Central Job Engine: Stale Worker Detection.

Verifies that the Engine can detect workers that stop heartbeating,
mark them stale, and reassign their jobs to healthy workers.
"""

import json
import time

import pytest

from .constants import *
from .helpers import *


class TestStaleDetection:
    """Workers that stop heartbeating must be detected and marked stale."""

    def test_worker_stops_sending_heartbeat_marked_stale(self, engine_with_heartbeat_check, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.heartbeat()
        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)

        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_STALE,
            timeout=HEARTBEAT_TIMEOUT_SECONDS + 5,
        ), "Worker should be marked stale after heartbeat timeout"

    def test_stale_event_published(self, engine_with_heartbeat_check, docker_redis_client, captured_events):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.heartbeat()

        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_STALE,
            timeout=HEARTBEAT_TIMEOUT_SECONDS + 5,
        )

        assert_event(captured_events, CH_WORKER_STALE, hostname=worker.hostname)

    def test_active_stale_worker_jobs_reassigned(self, engine_with_heartbeat_check, docker_redis_client):
        stale_worker = FakeWorker(docker_redis_client, hostname="stale-worker@test")
        healthy_worker = FakeWorker(docker_redis_client, hostname="healthy-worker@test")

        stale_worker.register()
        assert wait_for_redis_key(docker_redis_client, stale_worker.worker_key())

        job_id = "stale-reassign-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, stale_worker.hostname, timeout=3.0,
        )

        healthy_worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, healthy_worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        stale_worker.heartbeat()

        # Keep healthy_worker alive with periodic heartbeats while stale_worker goes stale
        wait_start = time.time()
        while time.time() - wait_start < HEARTBEAT_TIMEOUT_SECONDS + 5:
            if docker_redis_client.hget(stale_worker.worker_key(), "status") == WORKER_STATUS_STALE:
                break
            healthy_worker.heartbeat()
            time.sleep(2)

        # Confirm stale worker is marked stale
        assert docker_redis_client.hget(stale_worker.worker_key(), "status") == WORKER_STATUS_STALE, \
            "Stale worker should be marked stale"

        # Job should be reassigned to healthy worker
        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) == healthy_worker.hostname,
            timeout=10,
        ), f"Job {job_id} should be reassigned to healthy worker"

    def test_stale_worker_with_no_jobs_not_reassigned(self, engine_with_heartbeat_check, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.heartbeat()

        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_STALE,
            timeout=HEARTBEAT_TIMEOUT_SECONDS + 5,
        ), "Idle worker should still be marked stale"

        assert wait_for_queue_length(docker_redis_client, 0), "No jobs should be queued due to idle worker going stale"

    def test_stale_worker_recovers_with_heartbeat(self, engine_with_heartbeat_check, docker_redis_client):
        worker = FakeWorker(docker_redis_client)
        worker.register()
        assert wait_for_redis_key(docker_redis_client, worker.worker_key())

        worker.heartbeat()

        assert wait_for_redis_hash_field_value(
            docker_redis_client, worker.worker_key(), "status", WORKER_STATUS_STALE,
            timeout=HEARTBEAT_TIMEOUT_SECONDS + 5,
        )

        worker.heartbeat()
        time.sleep(0.5)

        assert_worker_status(docker_redis_client, worker.hostname, WORKER_STATUS_IDLE)

    def test_stale_worker_reassign_event_published(self, engine_with_heartbeat_check, docker_redis_client, captured_events):
        stale_worker = FakeWorker(docker_redis_client, hostname="stale-event-worker@test")
        healthy_worker = FakeWorker(docker_redis_client, hostname="healthy-event-worker@test")

        stale_worker.register()
        assert wait_for_redis_key(docker_redis_client, stale_worker.worker_key())

        job_id = "stale-event-reassign-001"
        publish_job_request(docker_redis_client, job_id)
        assert wait_for_redis_hash_field_value(
            docker_redis_client, ACTIVE_JOBS, job_id, stale_worker.hostname, timeout=3.0,
        )

        healthy_worker.register()
        assert wait_for_redis_hash_field_value(
            docker_redis_client, healthy_worker.worker_key(), "status", WORKER_STATUS_IDLE, timeout=3.0,
        )

        stale_worker.heartbeat()

        wait_start = time.time()
        while time.time() - wait_start < HEARTBEAT_TIMEOUT_SECONDS + 5:
            if docker_redis_client.hget(stale_worker.worker_key(), "status") == WORKER_STATUS_STALE:
                break
            healthy_worker.heartbeat()
            time.sleep(2)

        assert docker_redis_client.hget(stale_worker.worker_key(), "status") == WORKER_STATUS_STALE, \
            "Stale worker should be marked stale"

        assert wait_for_condition(
            lambda: docker_redis_client.hget(ACTIVE_JOBS, job_id) == healthy_worker.hostname,
            timeout=10,
        ), f"Job {job_id} should be reassigned to healthy worker"

        assert_event(captured_events, CH_WORKER_STALE, hostname=stale_worker.hostname)
        assert_event(captured_events, CH_JOB_REASSIGNED, job_id=job_id)
