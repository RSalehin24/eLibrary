"""Stale detector — identifies workers that have stopped heartbeating."""

from datetime import datetime, timezone

from .constants import *
from .worker_registry import get_all_workers, set_worker_status, worker_key
from .job_queue import get_active_jobs_for_worker, unassign_job, enqueue_job, publish_event


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def check_stale_workers(redis, heartbeat_timeout=HEARTBEAT_TIMEOUT_SECONDS):
    """
    Check all workers and mark stale any that haven't heartbeaten
    within the timeout. Returns list of stale worker hostnames.
    """
    stale_workers = []
    workers = get_all_workers(redis)

    for w in workers:
        hostname = w["hostname"]
        status = w.get("status", "")

        if status == WORKER_STATUS_OFFLINE:
            continue

        last_heartbeat_str = w.get("last_heartbeat", "")
        if not last_heartbeat_str:
            continue

        try:
            last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
            elapsed = (datetime.now(timezone.utc) - last_heartbeat).total_seconds()
        except (ValueError, TypeError):
            elapsed = 0

        if elapsed > heartbeat_timeout:
            set_worker_status(redis, hostname, WORKER_STATUS_STALE)
            stale_workers.append(hostname)

            publish_event(redis, CH_WORKER_STALE, hostname=hostname)

            active_jobs = get_active_jobs_for_worker(redis, hostname)
            for job_id in active_jobs:
                unassign_job(redis, job_id)
                enqueue_job(redis, job_id)
                publish_event(redis, CH_JOB_REASSIGNED, job_id=job_id, from_worker=hostname)

    return stale_workers
