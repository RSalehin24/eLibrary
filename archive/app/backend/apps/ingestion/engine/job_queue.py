"""Job queue — manages the pending job queue and active job assignments."""

import json
from datetime import datetime, timezone

from .constants import *


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def enqueue_job(redis, job_id):
    """Add a job to the end of the pending queue."""
    redis.rpush(PENDING_QUEUE, str(job_id))


def requeue_job(redis, job_id):
    """Return a job to the front of the pending queue (preserve order)."""
    redis.lpush(PENDING_QUEUE, str(job_id))


def dequeue_job(redis):
    """Remove and return the next job from the front of the queue, or None."""
    job_id = redis.lpop(PENDING_QUEUE)
    return job_id


def assign_job(redis, job_id, hostname):
    """Assign a job to a worker."""
    job_id = str(job_id)
    redis.hset(ACTIVE_JOBS, job_id, hostname)
    set_worker_current_job(redis, hostname, job_id)
    set_worker_status(redis, hostname, WORKER_STATUS_PROCESSING)


def unassign_job(redis, job_id):
    """Remove a job from active assignments."""
    job_id = str(job_id)
    hostname = redis.hget(ACTIVE_JOBS, job_id)
    redis.hdel(ACTIVE_JOBS, job_id)
    if hostname:
        wkey = WORKER_KEY.format(hostname=hostname)
        if redis.exists(wkey):
            current = redis.hget(wkey, "current_job")
            if current == job_id:
                redis.hset(wkey, "current_job", "")
                current_status = redis.hget(wkey, "status")
                if current_status not in (WORKER_STATUS_OFFLINE, WORKER_STATUS_STALE):
                    redis.hset(wkey, "status", WORKER_STATUS_IDLE)
    return hostname


def get_active_job_worker(redis, job_id):
    """Return the hostname of the worker assigned to a job, or None."""
    return redis.hget(ACTIVE_JOBS, str(job_id))


def get_all_active_jobs(redis):
    """Return dict of {job_id: worker_hostname} for all active jobs."""
    return redis.hgetall(ACTIVE_JOBS)


def get_active_jobs_for_worker(redis, hostname):
    """Return list of job IDs assigned to a specific worker."""
    jobs = []
    for job_id, worker in redis.hgetall(ACTIVE_JOBS).items():
        if worker == hostname:
            jobs.append(job_id)
    return jobs


def get_queue_length(redis):
    """Return the number of pending jobs."""
    return redis.llen(PENDING_QUEUE)


def get_active_count(redis):
    """Return the number of active (assigned) jobs."""
    return redis.hlen(ACTIVE_JOBS)


def set_worker_status(redis, hostname, status):
    """Set the worker's status field."""
    from .worker_registry import worker_key
    key = worker_key(hostname)
    if redis.exists(key):
        redis.hset(key, "status", status)


def set_worker_current_job(redis, hostname, job_id):
    """Set the worker's current job field."""
    from .worker_registry import worker_key
    key = worker_key(hostname)
    if redis.exists(key):
        redis.hset(key, "current_job", job_id or "")


def publish_event(redis, channel, **data):
    """Publish an event to a Redis channel."""
    data["timestamp"] = now_iso()
    redis.publish(channel, json.dumps(data))
