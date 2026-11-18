"""Dispatch — publishes job requests to the Engine from Django code."""

import json
from datetime import datetime, timezone

from .constants import CH_JOB_REQUEST, PENDING_QUEUE
from .redis_client import create_redis_client


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def dispatch_job(job_id, job_type="reprocess", handler="process_submission", **kwargs):
    """
    Publish a job request to the Engine via Redis Pub/Sub.

    This function replaces Celery's apply_async() for job dispatch.
    Django calls this after creating/saving a ProcessingJob record.
    """
    redis = create_redis_client()
    try:
        redis.hset("engine:job:handlers", str(job_id), handler)
        redis.rpush(PENDING_QUEUE, str(job_id))
        redis.publish(CH_JOB_REQUEST, json.dumps({
            "job_id": str(job_id),
            "job_type": job_type,
            "handler": handler,
            "args": kwargs,
            "timestamp": now_iso(),
        }))
    finally:
        redis.close()

