"""Worker registry — maintains real-time state of all workers in Redis."""

import json
from datetime import datetime, timezone

from .constants import *


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def worker_key(hostname):
    return WORKER_KEY.format(hostname=hostname)


def register_worker(redis, hostname, capabilities, pool_size=1, concurrency=1):
    """Register a worker in the Redis registry."""
    key = worker_key(hostname)
    redis.hset(key, "hostname", hostname)
    redis.hset(key, "capabilities", json.dumps(capabilities))
    redis.hset(key, "pool_size", pool_size)
    redis.hset(key, "concurrency", concurrency)
    redis.hset(key, "status", WORKER_STATUS_IDLE)
    redis.hset(key, "current_job", "")
    redis.hset(key, "registered_at", now_iso())
    redis.hset(key, "last_heartbeat", now_iso())


def deregister_worker(redis, hostname):
    """
    Remove a worker from the Redis registry.
    If the worker has an active job, requeue it.
    """
    key = worker_key(hostname)
    current_job = redis.hget(key, "current_job")
    if current_job:
        redis.rpush(PENDING_QUEUE, current_job)
        redis.hdel(ACTIVE_JOBS, current_job)
    redis.delete(key)


def update_heartbeat(redis, hostname):
    """Update a worker's last heartbeat timestamp."""
    key = worker_key(hostname)
    if not redis.exists(key):
        return False
    redis.hset(key, "last_heartbeat", now_iso())
    status = redis.hget(key, "status")
    if status == WORKER_STATUS_STALE:
        redis.hset(key, "status", WORKER_STATUS_IDLE)
    return True


def set_worker_status(redis, hostname, status):
    """Set the worker's status."""
    key = worker_key(hostname)
    if redis.exists(key):
        redis.hset(key, "status", status)


def set_worker_current_job(redis, hostname, job_id):
    """Set the worker's current job."""
    key = worker_key(hostname)
    if redis.exists(key):
        redis.hset(key, "current_job", job_id or "")


def get_worker(redis, hostname):
    """Get worker details as a dict, or None if not found."""
    key = worker_key(hostname)
    if not redis.exists(key):
        return None
    data = redis.hgetall(key)
    if "capabilities" in data:
        data["capabilities"] = json.loads(data["capabilities"])
    return data


def get_all_workers(redis):
    """Return all registered workers as a list of dicts."""
    workers = []
    cursor = 0
    pattern = WORKER_KEY.replace("{hostname}", "*")
    while True:
        cursor, keys = redis.scan(cursor=cursor, match=pattern, count=100)
        for key in keys:
            hostname = key.split(":", 2)[2]
            worker = get_worker(redis, hostname)
            if worker:
                workers.append(worker)
        if cursor == 0:
            break
    return workers


def find_idle_worker(redis, required_capability=None):
    """
    Find an idle worker, optionally filtering by capability.
    Returns the worker's hostname or None.
    """
    workers = get_all_workers(redis)
    for w in workers:
        if w.get("status") != WORKER_STATUS_IDLE:
            continue
        if required_capability and required_capability not in w.get("capabilities", []):
            continue
        return w["hostname"]
    return None


def get_worker_count(redis, status=None):
    """Count workers, optionally filtered by status."""
    workers = get_all_workers(redis)
    if status:
        return sum(1 for w in workers if w.get("status") == status)
    return len(workers)
