"""Recovery — reconciles Engine state on restart for self-healing."""

from .constants import *
from .worker_registry import get_all_workers, set_worker_status
from .job_queue import (
    get_all_active_jobs,
    get_queue_length,
    unassign_job,
    enqueue_job,
    publish_event,
)


def recover_state(redis, heartbeat_timeout=HEARTBEAT_TIMEOUT_SECONDS):
    """
    On engine restart, reconcile state:
    1. Mark workers that went offline as OFFLINE.
    2. Requeue jobs assigned to dead/offline workers.
    3. Re-queue any jobs left in pending queue.
    Returns a dict of {recovered_jobs: int, stale_workers: int}.
    """
    recovered_jobs = 0
    stale_workers = 0

    workers = get_all_workers(redis)

    for w in workers:
        hostname = w["hostname"]
        status = w.get("status", "")
        last_heartbeat_str = w.get("last_heartbeat", "")

        if status in (WORKER_STATUS_OFFLINE, WORKER_STATUS_STALE):
            set_worker_status(redis, hostname, WORKER_STATUS_OFFLINE)
            stale_workers += 1

            active_jobs = _get_active_jobs_for_worker(redis, hostname)
            for job_id in active_jobs:
                unassign_job(redis, job_id)
                enqueue_job(redis, job_id)
                publish_event(redis, CH_JOB_REASSIGNED, job_id=job_id, from_worker=hostname)
                recovered_jobs += 1

    existing_hostnames = {w["hostname"] for w in workers}
    active_jobs = get_all_active_jobs(redis)
    for job_id, worker_hostname in active_jobs.items():
        if worker_hostname not in existing_hostnames:
            unassign_job(redis, job_id)
            enqueue_job(redis, job_id)
            publish_event(redis, CH_JOB_REASSIGNED, job_id=job_id, from_worker=worker_hostname)
            recovered_jobs += 1

    return {
        "recovered_jobs": recovered_jobs,
        "stale_workers": stale_workers,
    }


def _get_active_jobs_for_worker(redis, hostname):
    """Helper: return list of job IDs assigned to a worker."""
    jobs = []
    for job_id, worker in redis.hgetall(ACTIVE_JOBS).items():
        if worker == hostname:
            jobs.append(job_id)
    return jobs
