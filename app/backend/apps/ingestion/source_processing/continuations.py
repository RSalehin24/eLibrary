from django.db import transaction
from django.utils import timezone

from apps.processing.job_models import JobAttempt, JobDispatch
from apps.processing.jobs.attempts import owned_job, settle_requested_action


class CollectionYield(RuntimeError):
    pass


@transaction.atomic
def continue_collection(ownership):
    job = owned_job(ownership)
    if settle_requested_action(job):
        return
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        stage="collection_checkpointed", finished_at=timezone.now()
    )
    job.active_attempt = None
    job.state, job.error_code = "queued", ""
    job.generation += 1
    job.available_at = timezone.now()
    job.checkpoint = {**job.checkpoint, "continuation": True}
    job.save()
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
