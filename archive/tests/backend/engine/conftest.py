"""Pytest fixtures for Central Job Engine integration tests.

These fixtures connect to the ACTUAL Redis and PostgreSQL services
running in Docker. No mocking — tests run against real infrastructure.
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import redis as redis_module

from .constants import *


def _get_redis_host():
    """Get Redis host from environment or default to Docker hostname."""
    return os.environ.get("REDIS_HOST", os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"))


def _parse_redis_url(url):
    """Parse a redis:// URL into host/port/db."""
    if url.startswith("redis://"):
        parts = url[8:].split("/")
        hostport = parts[0].split(":")
        host = hostport[0]
        port = int(hostport[1]) if len(hostport) > 1 else 6379
        db = int(parts[1]) if len(parts) > 1 else 0
        return host, port, db
    return url, 6379, 0


@pytest.fixture(scope="session")
def docker_redis_host():
    """Return the Redis hostname from Docker compose or env."""
    url = _get_redis_host()
    host, port, db = _parse_redis_url(url)
    return host, port, db


@pytest.fixture(scope="session")
def docker_redis_client(docker_redis_host):
    """
    Connect to the ACTUAL Redis running in Docker.
    This is the real Redis used by the application.
    """
    host, port, db = docker_redis_host
    client = redis_module.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    client.ping()  # Verify connection
    yield client


@pytest.fixture(autouse=True)
def clean_engine_keys(docker_redis_client):
    """
    Remove all engine-related keys before each test.
    This ensures test isolation without restarting Redis.
    """
    for key in docker_redis_client.scan_iter("engine:*"):
        docker_redis_client.delete(key)
    yield
    # Reset connection pool between tests to avoid stale connection state
    docker_redis_client.connection_pool.disconnect()


@pytest.fixture
def engine(docker_redis_client, request):
    """
    Start the Central Job Engine in a background thread.
    The engine subscribes to Redis channels and processes events.
    
    This is a lightweight in-process engine suitable for testing.
    Yields the engine instance for direct interaction.
    """
    from apps.ingestion.engine.engine import JobEngine

    eng = JobEngine(docker_redis_client)
    eng.start()

    def fin():
        eng.stop()

    request.addfinalizer(fin)
    # Give the engine a moment to subscribe to channels
    time.sleep(0.2)
    return eng


@pytest.fixture
def engine_with_heartbeat_check(docker_redis_client, request):
    """
    Start the Engine with an active heartbeat timeout checker.
    The checker runs every 2 seconds and marks stale workers.
    """
    from apps.ingestion.engine.engine import JobEngine

    eng = JobEngine(
        docker_redis_client,
        heartbeat_timeout=HEARTBEAT_TIMEOUT_SECONDS,
        heartbeat_check_interval=2.0,
    )
    eng.start()

    def fin():
        eng.stop()

    request.addfinalizer(fin)
    time.sleep(0.2)
    return eng


@pytest.fixture
def workers(docker_redis_client):
    """
    Factory fixture that creates FakeWorker helpers.
    Returns a function that creates and registers workers.
    
    Usage:
        w1, w2 = workers(2)
        w1.register()
    """
    created = []

    def _make_workers(count=1, capabilities=None):
        from .helpers import FakeWorker

        result = []
        for i in range(count):
            worker = FakeWorker(docker_redis_client, capabilities=capabilities)
            created.append(worker)
            result.append(worker)
        return result[0] if count == 1 else result

    yield _make_workers

    # Deregister any workers that were created but not cleaned up
    for worker in created:
        try:
            docker_redis_client.delete(worker.worker_key())
        except Exception:
            pass


@pytest.fixture
def jobs_in_db(request):
    """
    Create ProcessingJob records in the database.
    Uses Django's test database (which uses the Docker PostgreSQL).
    
    Usage:
        job = jobs_in_db()  # creates one job
        job1, job2 = jobs_in_db(2)  # creates two jobs
    """
    from django.utils import timezone
    from apps.ingestion.models import BookSubmission, ProcessingJob, JobStatus, SubmissionStatus, SubmissionInputType, ResolutionStatus

    created_jobs = []

    def _create_jobs(count=1, job_type="reprocess", status="queued", **kwargs):
        result = []
        for i in range(count):
            submission = BookSubmission.objects.create(
                input_type=SubmissionInputType.URL,
                origin="user",
                original_input=f"https://example.com/books/test-{i}/",
                normalized_input=f"https://example.com/books/test-{i}/",
                resolved_url=f"https://example.com/books/test-{i}/",
                resolution_status=ResolutionStatus.RESOLVED,
                status=SubmissionStatus.QUEUED,
            )
            job = ProcessingJob.objects.create(
                submission=submission,
                job_type=job_type,
                status=status,
                **kwargs,
            )
            created_jobs.append(job)
            result.append(job)
        return result[0] if count == 1 else result

    yield _create_jobs

    # Cleanup
    for job in created_jobs:
        try:
            job.submission.delete()
            job.delete()
        except Exception:
            pass


@pytest.fixture
def captured_events(docker_redis_client):
    """
    Subscribe to engine event channels and capture all events.
    Useful for asserting that specific events were published.
    """
    import threading as _threading

    events = []
    lock = _threading.Lock()

    pubsub = docker_redis_client.pubsub()
    channels = [
        CH_JOB_ASSIGNED,
        CH_JOB_REASSIGNED,
        CH_JOB_COMPLETED,
        CH_WORKER_STALE,
    ]

    def handler(message):
        with lock:
            events.append({
                "channel": message["channel"],
                "data": json.loads(message["data"]),
            })

    for ch in channels:
        pubsub.subscribe(**{ch: handler})

    thread = pubsub.run_in_thread(sleep_time=0.01, daemon=True)

    yield events

    thread.stop()
    try:
        pubsub.unsubscribe()
    except Exception:
        pass
    try:
        pubsub.close()
    except Exception:
        pass



