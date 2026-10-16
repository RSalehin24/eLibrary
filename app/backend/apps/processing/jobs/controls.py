from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobState,
    JobDispatch,
    RequestedJobAction,
)
from apps.processing.jobs.attempts import settle_requested_action
from apps.processing.jobs.commands import JobConflict


@transaction.atomic
def request_stop(identifier: UUID, action: RequestedJobAction):
    if action not in {RequestedJobAction.PAUSE, RequestedJobAction.CANCEL}:
        raise ValueError("Unknown job control action.")
    job = BackgroundJob.objects.select_for_update().get(pk=identifier)
    if job.state not in {
        BackgroundJobState.RUNNING,
        BackgroundJobState.QUEUED,
        BackgroundJobState.RETRY_WAIT,
        BackgroundJobState.PAUSED,
    }:
        raise JobConflict("This job has already finished.")
    if (
        job.requested_action == RequestedJobAction.CANCEL
        and action == RequestedJobAction.PAUSE
    ):
        raise JobConflict("Cancellation has already been requested.")
    job.requested_action = action
    job.save(update_fields=["requested_action", "updated_at"])
    if job.state != BackgroundJobState.RUNNING:
        settle_requested_action(job)
    return job


@transaction.atomic
def resume_job(identifier: UUID):
    job = BackgroundJob.objects.select_for_update().get(pk=identifier)
    if job.state != BackgroundJobState.PAUSED:
        raise JobConflict("Only a paused job can be resumed.")
    job.generation += 1
    job.state = BackgroundJobState.QUEUED
    job.requested_action = RequestedJobAction.NONE
    job.available_at = timezone.now()
    job.finished_at = None
    job.save()
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    return job
