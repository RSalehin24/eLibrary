"""
Celery signal handlers for the Central Job Engine.

These handlers run inside each Celery worker process and push events
to Redis Pub/Sub channels that the Engine listens to:

  - worker_process_init → register via engine:channel:worker:register
  - heartbeat_sent      → heartbeat via engine:channel:worker:heartbeat
  - task_prerun         → claim job (status → processing)
  - task_postrun        → complete / fail via engine:channel:worker:done
  - worker_process_shutdown → deregister via engine:channel:worker:deregister

Also starts a background listener thread that subscribes to
CH_JOB_ASSIGNED, allowing the Engine to dispatch jobs directly
to workers without going through Celery's broker.
"""

import json
import logging
import os
import socket
import threading
import time
from datetime import datetime, timezone

from celery import signals

from apps.ingestion.engine.redis_client import create_redis_client
from apps.ingestion.engine.constants import (
    CH_WORKER_REGISTER,
    CH_WORKER_HEARTBEAT,
    CH_WORKER_DEREGISTER,
    CH_WORKER_DONE,
    CH_JOB_ASSIGNED,
)

logger = logging.getLogger(__name__)

_redis_client = None
_worker_hostname = None
_engine_listener_thread = None
_engine_listener_running = False


def _get_hostname():
    """Generate a unique worker hostname."""
    global _worker_hostname
    if _worker_hostname:
        return _worker_hostname
    host = socket.gethostname()
    pid = os.getpid()
    _worker_hostname = f"celery-{host}-{pid}@worker"
    return _worker_hostname


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client()
    return _redis_client


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _publish(channel, data):
    try:
        redis = _get_redis()
        redis.publish(channel, json.dumps(data))
    except Exception:
        logger.exception("Failed to publish event to %s", channel)


def _start_engine_listener():
    """Start background thread to listen for engine job assignments."""
    global _engine_listener_thread, _engine_listener_running
    if _engine_listener_thread is not None:
        return
    _engine_listener_running = True
    _engine_listener_thread = threading.Thread(
        target=_engine_listener_loop, daemon=True, name="engine-assignment-listener"
    )
    _engine_listener_thread.start()
    logger.info("Engine assignment listener started")


def _stop_engine_listener():
    """Stop the engine assignment listener thread."""
    global _engine_listener_running, _engine_listener_thread
    _engine_listener_running = False
    if _engine_listener_thread:
        _engine_listener_thread.join(timeout=3.0)
        _engine_listener_thread = None
    logger.info("Engine assignment listener stopped")


def _engine_listener_loop():
    """Listen for CH_JOB_ASSIGNED and execute jobs dispatched by the Engine."""
    redis = create_redis_client()
    pubsub = redis.pubsub()
    try:
        pubsub.subscribe(CH_JOB_ASSIGNED)
        while _engine_listener_running:
            message = pubsub.get_message(timeout=1.0)
            if not message or message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            job_id = data.get("job_id", "")
            handler = data.get("handler", "process_submission")
            assigned_worker = data.get("worker_hostname", "")
            hostname = _get_hostname()
            
            if assigned_worker != hostname:
                continue
                
            logger.info("Engine assigned job %s (handler=%s) to %s", job_id, handler, hostname)

            try:
                if handler == "process_submission":
                    from apps.ingestion.services.submissions import process_submission_job
                    process_submission_job(str(job_id), retry_count=0, task_id="engine")
                elif handler == "pipeline":
                    from apps.processing.services import kickoff_request_processing
                    kickoff_request_processing(str(job_id))
                else:
                    logger.warning("Unknown engine job handler: %s for job %s", handler, job_id)

                _publish(CH_WORKER_DONE, {
                    "hostname": hostname,
                    "job_id": str(job_id),
                    "status": "succeeded",
                    "handler": handler,
                    "timestamp": _now_iso(),
                })
            except Exception as exc:
                logger.exception("Engine job %s (handler=%s) failed", job_id, handler)
                _publish(CH_WORKER_DONE, {
                    "hostname": hostname,
                    "job_id": str(job_id),
                    "status": "failed",
                    "handler": handler,
                    "error_message": str(exc),
                    "timestamp": _now_iso(),
                })
    finally:
        try:
            pubsub.close()
        except Exception:
            pass
        try:
            redis.close()
        except Exception:
            pass


@signals.worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Register this worker with the Engine on startup."""
    hostname = _get_hostname()
    _publish(CH_WORKER_REGISTER, {
        "hostname": hostname,
        "capabilities": ["process_submission", "pipeline", "catalog_sync", "curation", "automation"],
        "pool_size": 1,
        "concurrency": 1,
        "timestamp": _now_iso(),
    })
    logger.info("Worker registered with Engine: %s", hostname)
    _start_engine_listener()


@signals.worker_process_shutdown.connect
def on_worker_process_shutdown(**kwargs):
    """Deregister this worker from the Engine on shutdown."""
    _stop_engine_listener()
    hostname = _get_hostname()
    _publish(CH_WORKER_DEREGISTER, {
        "hostname": hostname,
        "timestamp": _now_iso(),
    })
    logger.info("Worker deregistered from Engine: %s", hostname)

    global _redis_client
    if _redis_client:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None


@signals.heartbeat_sent.connect
def on_heartbeat_sent(**kwargs):
    """Send heartbeat to the Engine."""
    hostname = _get_hostname()
    _publish(CH_WORKER_HEARTBEAT, {
        "hostname": hostname,
        "timestamp": _now_iso(),
    })


@signals.task_prerun.connect
def on_task_prerun(task_id, task, **kwargs):
    """Notify Engine that a job has started processing."""
    hostname = _get_hostname()
    job_id = kwargs.get("args", (None,))[0] if kwargs.get("args") else None
    if job_id:
        _publish(CH_WORKER_HEARTBEAT, {
            "hostname": hostname,
            "job_id": str(job_id),
            "status": "processing",
            "timestamp": _now_iso(),
        })


@signals.task_postrun.connect
def on_task_postrun(task_id, task, state, retval, **kwargs):
    """Notify Engine that a job has completed or failed."""
    hostname = _get_hostname()
    job_id = kwargs.get("args", (None,))[0] if kwargs.get("args") else None
    if not job_id:
        return

    status = "succeeded" if state == "SUCCESS" else "failed"
    error_message = ""
    if state == "FAILURE":
        try:
            error_message = str(retval) if retval else "Unknown error"
        except Exception:
            error_message = "Unknown error"

    _publish(CH_WORKER_DONE, {
        "hostname": hostname,
        "job_id": str(job_id),
        "status": status,
        "error_message": error_message,
        "timestamp": _now_iso(),
    })
