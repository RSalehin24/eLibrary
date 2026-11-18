"""Engine API — inspection and management functions.

Provides functions to query engine state, workers, jobs, and queue.
These can be called from Django views or management commands.
"""

from .constants import *
from . import worker_registry as wr
from . import job_queue as jq


def list_workers(status=None):
    """Return all workers, optionally filtered by status."""
    from .redis_client import create_redis_client
    redis = create_redis_client()
    try:
        workers = wr.get_all_workers(redis)
        if status:
            workers = [w for w in workers if w.get("status") == status]
        return workers
    finally:
        redis.close()


def get_worker_detail(hostname):
    """Return details for a specific worker, or None."""
    from .redis_client import create_redis_client
    redis = create_redis_client()
    try:
        return wr.get_worker(redis, hostname)
    finally:
        redis.close()


def get_job_status(job_id):
    """Return status of a specific job: active worker or None."""
    from .redis_client import create_redis_client
    redis = create_redis_client()
    try:
        worker = jq.get_active_job_worker(redis, str(job_id))
        if worker:
            return {
                "job_id": str(job_id),
                "worker_hostname": worker,
                "status": WORKER_STATUS_PROCESSING,
            }
        return None
    finally:
        redis.close()


def get_queue_depth():
    """Return number of pending jobs in the queue."""
    from .redis_client import create_redis_client
    redis = create_redis_client()
    try:
        return jq.get_queue_length(redis)
    finally:
        redis.close()


def reassign_job(job_id, target_hostname):
    """
    Manually reassign a job to a specific worker.
    Returns True if successful, False otherwise.
    """
    from .redis_client import create_redis_client
    redis = create_redis_client()
    try:
        current_worker = jq.get_active_job_worker(redis, str(job_id))
        if current_worker:
            jq.unassign_job(redis, str(job_id))
        jq.assign_job(redis, str(job_id), target_hostname)
        jq.publish_event(
            redis, CH_JOB_REASSIGNED,
            job_id=str(job_id), from_worker=current_worker or "", to_worker=target_hostname,
        )
        return True
    finally:
        redis.close()


def get_engine_status():
    """Return overall engine health and stats."""
    from .redis_client import create_redis_client
    redis = create_redis_client()
    try:
        workers = wr.get_all_workers(redis)
        worker_count = len(workers)
        idle_count = sum(1 for w in workers if w.get("status") == WORKER_STATUS_IDLE)
        processing_count = sum(1 for w in workers if w.get("status") == WORKER_STATUS_PROCESSING)
        stale_count = sum(1 for w in workers if w.get("status") == WORKER_STATUS_STALE)
        queue_depth = jq.get_queue_length(redis)
        active_jobs = jq.get_active_count(redis)

        return {
            "running": True,
            "worker_count": worker_count,
            "idle_workers": idle_count,
            "processing_workers": processing_count,
            "stale_workers": stale_count,
            "queue_depth": queue_depth,
            "active_jobs": active_jobs,
        }
    finally:
        redis.close()
