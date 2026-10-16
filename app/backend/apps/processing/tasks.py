from uuid import UUID

from celery import shared_task
from django.conf import settings

from .jobs.worker import run_background_job
from .models import BookCreationRequest, BookCreationRequestState
from .services import (
    PROCESSING_SYNC_KEY_CATALOG,
    kickoff_request_processing,
    run_due_processing_automations,
    run_processing_maintenance,
    run_processing_runtime_tick,
    run_processing_sync_until_blocked,
    sync_state_task_payload,
)

run_processing_sync = run_processing_sync_until_blocked


@shared_task(
    acks_late=True,
    reject_on_worker_lost=True,
    ignore_result=True,
    soft_time_limit=settings.BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS,
    time_limit=settings.BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS + 60,
)
def run_background_job_task(dispatch_id):
    run_background_job(UUID(dispatch_id))


@shared_task(bind=True)
def run_processing_sync_task(self, singleton_key=PROCESSING_SYNC_KEY_CATALOG):
    state = run_processing_sync(
        singleton_key=singleton_key,
        task_id=self.request.id,
    )
    return sync_state_task_payload(state)


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def kickoff_book_creation_request_task(self, request_id):
    try:
        request = kickoff_request_processing(request_id)
    except BookCreationRequest.DoesNotExist:
        return {
            "request_id": str(request_id),
            "state": BookCreationRequestState.DELETED,
            "submission_id": "",
            "missing": True,
        }

    return {
        "request_id": str(request.id),
        "state": request.state,
        "submission_id": str(request.submission_id or ""),
    }


@shared_task
def run_due_processing_automations_task():
    return run_due_processing_automations()


@shared_task
def run_processing_maintenance_task():
    return run_processing_maintenance()


@shared_task
def run_processing_runtime_tick_task():
    return run_processing_runtime_tick()
