"""
Central Job Engine — main event loop.

Listens on Redis Pub/Sub channels and processes worker events,
performs job dispatch, and runs periodic stale worker checks.
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone

from .constants import *
from . import worker_registry as wr
from . import job_queue as jq
from .stale_detector import check_stale_workers
from .recovery import recover_state

logger = logging.getLogger(__name__)


class JobEngine:
    """
    The Central Job Engine.

    Subscribes to Redis Pub/Sub channels and processes events:
      - Worker register / heartbeat / deregister / done
      - Job request
    Periodically checks for stale workers.
    """

    def __init__(self, redis=None, heartbeat_timeout=HEARTBEAT_TIMEOUT_SECONDS,
                 heartbeat_check_interval=HEARTBEAT_CHECK_INTERVAL):
        from .redis_client import create_redis_client
        self.redis = redis or create_redis_client()
        self.heartbeat_timeout = heartbeat_timeout
        self.heartbeat_check_interval = heartbeat_check_interval
        self._running = False
        self._thread = None
        self._pubsub = None
        self._stale_thread = None

    def start(self):
        """Start the engine: recover state, subscribe to channels, begin loop."""
        if self._running:
            logger.warning("Engine is already running")
            return

        self._running = True

        recover_state(self.redis, self.heartbeat_timeout)

        self._dispatch_pending_jobs()

        self._pubsub = self.redis.pubsub()

        channel_handlers = {
            CH_WORKER_REGISTER: self._handle_worker_register,
            CH_WORKER_HEARTBEAT: self._handle_worker_heartbeat,
            CH_WORKER_DEREGISTER: self._handle_worker_deregister,
            CH_WORKER_DONE: self._handle_worker_done,
            CH_JOB_REQUEST: self._handle_job_request,
        }

        for ch, handler in channel_handlers.items():
            self._pubsub.subscribe(**{ch: handler})

        self._thread = threading.Thread(target=self._event_loop, daemon=True, name="engine-event-loop")
        self._thread.start()

        self._stale_thread = threading.Thread(
            target=self._stale_check_loop, daemon=True, name="engine-stale-check"
        )
        self._stale_thread.start()

        logger.info("JobEngine started")

    def stop(self):
        """Stop the engine gracefully."""
        self._running = False
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._pubsub:
            try:
                self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None
        self._thread = None
        self._stale_thread = None
        logger.info("JobEngine stopped")

    def is_running(self):
        return self._running

    def _event_loop(self):
        """Process pub/sub messages in a loop."""
        while self._running:
            try:
                message = self._pubsub.get_message(timeout=0.2)
            except Exception:
                if not self._running:
                    break
                logger.exception("Error in event loop get_message")
                continue
            if message and message["type"] == "message":
                try:
                    handler = self._pubsub.channels.get(message["channel"])
                    if handler:
                        handler(message)
                except Exception:
                    logger.exception("Error handling message on channel %s", message.get("channel"))

    def _stale_check_loop(self):
        """Periodically check for stale workers."""
        while self._running:
            time.sleep(self.heartbeat_check_interval)
            try:
                stale = check_stale_workers(self.redis, self.heartbeat_timeout)
                if stale:
                    self._dispatch_pending_jobs()
            except Exception:
                logger.exception("Error in stale worker check")

    def _handle_worker_register(self, message):
        data = self._decode(message)
        if not data:
            return
        wr.register_worker(
            self.redis,
            hostname=data.get("hostname"),
            capabilities=data.get("capabilities", []),
            pool_size=data.get("pool_size", 1),
            concurrency=data.get("concurrency", 1),
        )

        try:
            self._dispatch_pending_jobs()
        except Exception:
            logger.exception("Error dispatching pending jobs after worker registration")

    def _handle_worker_heartbeat(self, message):
        data = self._decode(message)
        if not data:
            return
        wr.update_heartbeat(self.redis, hostname=data.get("hostname"))

    def _handle_worker_deregister(self, message):
        data = self._decode(message)
        if not data:
            return
        wr.deregister_worker(self.redis, hostname=data.get("hostname"))

    def _handle_worker_done(self, message):
        data = self._decode(message)
        if not data:
            return
        job_id = data.get("job_id")
        hostname = data.get("hostname")
        status = data.get("status", "succeeded")
        error_message = data.get("error_message", "")

        jq.unassign_job(self.redis, job_id)
        self.redis.hdel("engine:job:handlers", job_id)

        wr.set_worker_status(self.redis, hostname, WORKER_STATUS_IDLE)
        wr.set_worker_current_job(self.redis, hostname, "")

        jq.publish_event(
            self.redis, CH_JOB_COMPLETED,
            job_id=job_id, status=status, error_message=error_message,
        )

        self._update_db_job_status(job_id, status, error_message)

        try:
            self._dispatch_pending_jobs()
        except Exception:
            logger.exception("Error dispatching pending jobs after worker done")

    def _handle_job_request(self, message):
        data = self._decode(message)
        if not data:
            return

        job_id = data.get("job_id")
        handler = data.get("handler", "process_submission")

        self.redis.hset("engine:job:handlers", job_id, handler)

        # Trigger dispatch of pending jobs. Since the job was already pushed to the queue
        # by dispatch_job, we call self._dispatch_pending_jobs() to handle assignment.
        self._dispatch_pending_jobs()

    def _try_assign_job(self, job_id, handler):
        """Try to assign a job to an idle worker matching the handler."""
        if not handler:
            handler = self.redis.hget("engine:job:handlers", job_id) or "process_submission"

        idle_worker = wr.find_idle_worker(self.redis, required_capability=handler)
        if not idle_worker:
            return False

        jq.assign_job(self.redis, job_id, idle_worker)

        jq.publish_event(
            self.redis, CH_JOB_ASSIGNED,
            job_id=job_id, worker_hostname=idle_worker, handler=handler,
        )

        self._update_db_job_assignment(job_id, idle_worker)
        return True

    def _dispatch_pending_jobs(self):
        """Try to dispatch queued jobs to idle workers."""
        dispatched = 0
        while True:
            # Inspect the first job in the queue without popping it
            job_id = self.redis.lindex(PENDING_QUEUE, 0)
            if not job_id:
                break

            handler = self.redis.hget("engine:job:handlers", job_id) or "process_submission"
            
            # Check if there is an idle worker that can handle this job
            idle_worker = wr.find_idle_worker(self.redis, required_capability=handler)
            if not idle_worker:
                # No worker available, keep the job in the queue and stop dispatching
                break

            # A worker is available! Now pop the job from the queue
            popped_id = self.redis.lpop(PENDING_QUEUE)
            if not popped_id:
                break

            # If the popped job changed (shouldn't happen since engine is single-threaded),
            # but to be safe, check it.
            if popped_id != job_id:
                # Requeue what we popped to the front and break
                self.redis.lpush(PENDING_QUEUE, popped_id)
                break

            # Assign the job to the worker
            jq.assign_job(self.redis, job_id, idle_worker)

            jq.publish_event(
                self.redis, CH_JOB_ASSIGNED,
                job_id=job_id, worker_hostname=idle_worker, handler=handler,
            )

            self._update_db_job_assignment(job_id, idle_worker)
            dispatched += 1

        return dispatched

    def _update_db_job_assignment(self, job_id, worker_hostname):
        """Update the ProcessingJob record with the assigned worker."""
        try:
            import uuid
            try:
                uuid.UUID(str(job_id))
            except ValueError:
                # Not a valid UUID, so it's a BookCreationRequest and doesn't have a ProcessingJob
                return
            from apps.ingestion.models.processing import ProcessingJob
            ProcessingJob.objects.filter(id=job_id).update(worker_hostname=worker_hostname)
        except Exception:
            logger.exception("Failed to update DB job assignment for %s", job_id)

    def _update_db_job_status(self, job_id, status, error_message=""):
        """Update the ProcessingJob record with completion status."""
        try:
            import uuid
            try:
                uuid.UUID(str(job_id))
            except ValueError:
                # Not a valid UUID, so it's a BookCreationRequest and doesn't have a ProcessingJob
                return
            from apps.ingestion.models.processing import ProcessingJob
            from django.utils import timezone
            update_fields = {
                "status": status,
                "finished_at": timezone.now(),
            }
            if error_message:
                update_fields["last_error"] = error_message
            ProcessingJob.objects.filter(id=job_id).update(**update_fields)
        except Exception:
            logger.exception("Failed to update DB job status for %s", job_id)

    def _decode(self, message):
        """Decode a pub/sub message payload."""
        try:
            return json.loads(message["data"])
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.exception("Failed to decode message: %s", message)
            return None
