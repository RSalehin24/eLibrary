"""Reusable test infrastructure for Central Job Engine tests."""

import json
import time
import uuid
from datetime import datetime, timezone

from .constants import *


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class FakeWorker:
    """
    Simulates a Celery worker that communicates with the Engine via Redis.
    
    In real life, a Celery worker would publish these events via signal handlers.
    This helper lets tests simulate those events without needing a real Celery worker.
    """

    def __init__(self, redis_client, hostname=None, capabilities=None):
        self.redis = redis_client
        self.hostname = hostname or f"test-worker-{uuid.uuid4().hex[:8]}@test"
        self.capabilities = capabilities or ["process_submission"]
        self.current_job_id = None

    def register(self):
        self.redis.publish(CH_WORKER_REGISTER, json.dumps({
            "hostname": self.hostname,
            "capabilities": self.capabilities,
            "pool_size": 1,
            "concurrency": 1,
            "timestamp": now_iso(),
        }))

    def heartbeat(self):
        self.redis.publish(CH_WORKER_HEARTBEAT, json.dumps({
            "hostname": self.hostname,
            "timestamp": now_iso(),
        }))

    def claim_job(self, job_id):
        self.current_job_id = job_id

    def complete_job(self, job_id, status="succeeded", error_message=""):
        self.redis.publish(CH_WORKER_DONE, json.dumps({
            "hostname": self.hostname,
            "job_id": job_id,
            "status": status,
            "error_message": error_message,
            "timestamp": now_iso(),
        }))
        self.current_job_id = None

    def fail_job(self, job_id, error_message="processing failed"):
        self.complete_job(job_id, status="failed", error_message=error_message)

    def deregister(self):
        self.redis.publish(CH_WORKER_DEREGISTER, json.dumps({
            "hostname": self.hostname,
            "timestamp": now_iso(),
        }))

    def worker_key(self):
        return WORKER_KEY.format(hostname=self.hostname)


def publish_job_request(redis_client, job_id, job_type="reprocess", handler="process_submission", **kwargs):
    """Publish a job request as Django would after creating a ProcessingJob."""
    redis_client.publish(CH_JOB_REQUEST, json.dumps({
        "job_id": str(job_id),
        "job_type": job_type,
        "handler": handler,
        "args": kwargs,
        "timestamp": now_iso(),
    }))


def wait_for_redis_key(redis_client, key, timeout=5.0):
    """Wait for a Redis key to exist, or until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if redis_client.exists(key):
            return True
        time.sleep(0.1)
    return False


def wait_for_redis_key_value(redis_client, key, expected_value, timeout=5.0):
    """Wait for a Redis key to have an expected value, or until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = redis_client.get(key)
        if value == expected_value:
            return True
        time.sleep(0.1)
    return False


def wait_for_redis_hash_field(redis_client, key, field, timeout=5.0):
    """Wait for a Redis hash to have a specific field, or until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if redis_client.hexists(key, field):
            return True
        time.sleep(0.1)
    return False


def wait_for_redis_hash_field_value(redis_client, key, field, expected_value, timeout=5.0):
    """Wait for a Redis hash field to have an expected value, or until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = redis_client.hget(key, field)
        if value == expected_value:
            return True
        time.sleep(0.1)
    return False


def wait_for_queue_length(redis_client, expected_length, timeout=5.0):
    """Wait for the pending queue to reach an expected length."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        length = redis_client.llen(PENDING_QUEUE)
        if length == expected_length:
            return True
        time.sleep(0.1)
    return False


def wait_for_condition(condition_fn, timeout=5.0, interval=0.1):
    """
    Generic wait for a condition function to return True.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition_fn():
            return True
        time.sleep(interval)
    return False


def assert_worker_status(redis_client, hostname, expected_status):
    """Assert that a worker has an expected status in the registry."""
    key = WORKER_KEY.format(hostname=hostname)
    status = redis_client.hget(key, "status")
    assert status == expected_status, (
        f"Worker {hostname} expected status '{expected_status}' but got '{status}'"
    )


def assert_worker_field(redis_client, hostname, field, expected_value):
    """Assert that a worker hash has a specific field value."""
    key = WORKER_KEY.format(hostname=hostname)
    actual = redis_client.hget(key, field)
    assert actual == expected_value, (
        f"Worker {hostname}.{field} expected '{expected_value}' but got '{actual}'"
    )


def assert_job_active(redis_client, job_id, expected_worker=None):
    """Assert a job is in the active jobs hash, optionally assigned to a specific worker."""
    worker = redis_client.hget(ACTIVE_JOBS, str(job_id))
    assert worker is not None, f"Job {job_id} is not in active jobs"
    if expected_worker is not None:
        assert worker == expected_worker, (
            f"Job {job_id} expected worker '{expected_worker}' but got '{worker}'"
        )


def assert_job_not_active(redis_client, job_id):
    """Assert a job is NOT in the active jobs hash."""
    worker = redis_client.hget(ACTIVE_JOBS, str(job_id))
    assert worker is None, f"Job {job_id} should not be active but is assigned to '{worker}'"


def assert_event(event_list, channel, **expected_data):
    """
    Assert that an event with given channel and data fields was captured.
    Only checks the fields present in expected_data (partial match).
    """
    for event in event_list:
        if event["channel"] != channel:
            continue
        matches = all(
            event["data"].get(k) == v
            for k, v in expected_data.items()
        )
        if matches:
            return
    raise AssertionError(
        f"Expected event on '{channel}' with {expected_data} not found "
        f"among {len(event_list)} captured events"
    )
