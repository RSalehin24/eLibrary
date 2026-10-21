import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.processing.job_models import BackgroundJob, JobDispatch
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.requests import require_processing_manager

from .classification import VALIDATOR_VERSION
from .collection_index import linked_book_entries
from .documents import read_source_result
from .verification import source_verification

logger = logging.getLogger(__name__)
VALIDATION_WAIT_ERRORS = {"source_layout_unknown", "source_description_only"}


def validation_wait_is_current(job):
    expected = job.checkpoint.get(
        "source_revision", job.input.get("command", {}).get("source_revision")
    )
    attempted = (job.checkpoint.get("source_validation_recovery") or {}).get(
        "validator_version", 0
    )
    return (
        job.kind == "process_source"
        and job.state == "retry_wait"
        and job.error_code in VALIDATION_WAIT_ERRORS
        and not job.book_id
        and not job.active_attempt_id
        and not job.requested_action
        and job.source_record is not None
        and not job.source_record.catalog_book_id
        and job.source_record.updated_at.isoformat() == expected
        and hasattr(job, "source_edition")
        and job.source_edition.validator_version < VALIDATOR_VERSION
        and attempted < VALIDATOR_VERSION
        and bool(job.source_edition.document_reference)
    )


def validator_can_recollect(job):
    try:
        result = read_source_result(job.pk, job.source_edition.document_reference)
    except ExecutionFailure as error:
        logger.warning(
            "Cannot inspect retained source validation for %s: %s",
            job.pk,
            error.failure.code,
        )
        return False
    if source_verification(result)["verified"]:
        return True
    snapshot = result.get("source_snapshot", {})
    raw = snapshot.get("raw_scrape_payload", {})
    return bool(
        not raw.get("content_items")
        and linked_book_entries(
            raw.get("main_content", ""), snapshot.get("canonical_url", "")
        )
    )


def queue_validator_recollection(job):
    previous = job.source_edition.validator_version
    job.checkpoint = {
        key: value
        for key, value in job.checkpoint.items()
        if key not in {"document_ref", "source_summary"}
    }
    job.checkpoint["source_validation_recovery"] = {
        "validator_version": VALIDATOR_VERSION
    }
    job.state, job.error_code, job.finished_at = "queued", "", None
    job.available_at, job.generation = timezone.now(), job.generation + 1
    job.save()
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    AuditLog.objects.create(
        actor=job.requested_by,
        verb="source.recover_validation",
        target_type=job._meta.label_lower,
        target_id=str(job.pk),
        payload={"previous_version": previous, "validator_version": VALIDATOR_VERSION},
    )
    return job


@transaction.atomic
def recover_source_validator(identifier):
    snapshot = BackgroundJob.objects.only("requested_by_id").get(pk=identifier)
    if snapshot.requested_by_id is None:
        return None
    actor = User.objects.select_for_update(no_key=True).get(pk=snapshot.requested_by_id)
    try:
        require_processing_manager(actor)
    except PermissionDenied:
        return None
    job = (
        BackgroundJob.objects.select_for_update(of=("self",))
        .select_related("source_record", "source_edition")
        .get(pk=identifier)
    )
    job.requested_by = actor
    if not validation_wait_is_current(job) or not validator_can_recollect(job):
        return None
    return queue_validator_recollection(job)


def recover_updated_source_validation():
    candidates = (
        BackgroundJob.objects.filter(
            kind="process_source",
            state="retry_wait",
            error_code__in=VALIDATION_WAIT_ERRORS,
            book__isnull=True,
            source_edition__validator_version__lt=VALIDATOR_VERSION,
        )
        .order_by("created_at", "id")
        .values_list("pk", flat=True)[:50]
    )
    return sum(
        recover_source_validator(identifier) is not None for identifier in candidates
    )
