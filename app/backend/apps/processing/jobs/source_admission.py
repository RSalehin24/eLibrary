from django.db import transaction

from apps.common.models import AuditLog
from apps.processing.job_models import BackgroundJob, JobDispatch


@transaction.atomic
def fence_source_dispatch(identifier):
    job = (
        BackgroundJob.objects.select_for_update(skip_locked=True)
        .filter(
            pk=identifier, kind="process_source", state__in=["queued", "retry_wait"]
        )
        .first()
    )
    if (
        job is None
        or not job.dispatches.filter(
            generation=job.generation, state="published"
        ).exists()
    ):
        return False
    job.generation += 1
    job.save(update_fields=["generation", "updated_at"])
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    AuditLog.objects.create(
        verb="source.dispatch.refence",
        target_type=job._meta.label_lower,
        target_id=str(job.pk),
        payload={"generation": job.generation},
    )
    return True
