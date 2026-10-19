from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.processing.job_models import BackgroundJob

from .documents import read_source_result
from .recovery import restart_repaired_source
from .verification import source_verification


def validation_recovery_evidence(job):
    if (
        job.kind != "process_source"
        or job.book_id
        or job.state not in {"failed", "needs_attention"}
        or job.error_code != "source_content_incomplete"
        or not job.checkpoint.get("document_ref")
    ):
        return None
    evidence = source_verification(
        read_source_result(job.pk, job.checkpoint["document_ref"])
    )
    if evidence["verified"] or evidence["classification"] == "unavailable_content":
        return evidence
    return None


@transaction.atomic
def recover_source_validation(identifier):
    job = (
        BackgroundJob.objects.select_for_update(of=("self",))
        .select_related("requested_by")
        .get(pk=identifier)
    )
    evidence = validation_recovery_evidence(job)
    if evidence is None or job.requested_by is None:
        return None
    repaired = restart_repaired_source(job.requested_by, job.pk)
    if evidence["classification"] == "unavailable_content":
        repaired.state, repaired.error_code = "retry_wait", "source_content_unavailable"
        repaired.available_at = timezone.now() + timedelta(hours=6)
        repaired.save(
            update_fields=["state", "error_code", "available_at", "updated_at"]
        )
        repaired.dispatches.filter(generation=repaired.generation).update(
            available_at=repaired.available_at
        )
    return repaired
