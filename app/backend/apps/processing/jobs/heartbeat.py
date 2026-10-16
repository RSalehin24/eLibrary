import logging
from contextlib import contextmanager
from threading import Event, Thread

from django.db import (
    close_old_connections,
    connection,
    connections,
    transaction,
)
from django.utils import timezone

from apps.processing.job_models import JobAttempt
from apps.processing.jobs.attempts import AttemptOwnership, owned_job
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

logger = logging.getLogger(__name__)
HEARTBEAT_INTERVAL_SECONDS = 15
HEARTBEAT_DATABASE_TIMEOUT_SECONDS = 5


@transaction.atomic
def heartbeat_attempt(ownership: AttemptOwnership):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            [str(HEARTBEAT_DATABASE_TIMEOUT_SECONDS * 1000)],
        )
    owned_job(ownership)
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        heartbeat_at=timezone.now()
    )


def heartbeat_loop(ownership, stop, failures):
    close_old_connections()
    try:
        while not stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            heartbeat_attempt(ownership)
    except Exception as error:
        failures.append(error)
        logger.exception(
            "Background job heartbeat stopped.", extra={"job_id": str(ownership.job_id)}
        )
    finally:
        connections.close_all()


@contextmanager
def maintain_heartbeat(ownership: AttemptOwnership):
    stop = Event()
    failures: list[Exception] = []
    thread = Thread(
        target=heartbeat_loop, args=(ownership, stop, failures), daemon=True
    )
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=HEARTBEAT_DATABASE_TIMEOUT_SECONDS + 1)
    if thread.is_alive() or failures:
        raise ExecutionFailure(FailureKind.TRANSIENT, "heartbeat_unavailable")
