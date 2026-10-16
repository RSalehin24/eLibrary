import logging

logger = logging.getLogger(__name__)


def update_db_job_assignment(job_id, worker_hostname):
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


def update_db_job_status(job_id, status, error_message=""):
    """Update the ProcessingJob record with completion status."""
    try:
        import uuid
        try:
            uuid.UUID(str(job_id))
        except ValueError:
            # Not a valid UUID, so it's a BookCreationRequest and doesn't have a ProcessingJob
            return
        from django.utils import timezone

        from apps.ingestion.models.processing import ProcessingJob
        update_fields = {
            "status": status,
            "finished_at": timezone.now(),
        }
        if error_message:
            update_fields["last_error"] = error_message
        ProcessingJob.objects.filter(id=job_id).update(**update_fields)
    except Exception:
        logger.exception("Failed to update DB job status for %s", job_id)

