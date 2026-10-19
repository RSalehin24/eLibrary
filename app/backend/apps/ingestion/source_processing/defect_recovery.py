from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager
from apps.processing.jobs.source_defects import (
    SOURCE_DEFECT_CODES,
    source_code_version,
    source_defect_waits_for_code,
)

from .issues import available_source_choices
from .resolution import resolve_source_job

REGENERATED_CHECKPOINT_KEYS = {
    "exports_ref",
    "exports_verified",
    "staged_assets",
    "publication_id",
    "checksum",
    "asset_revision",
    "asset_checksum",
}


def defect_recovery_choice(job):
    if (
        job.kind != "process_source"
        or job.state not in {"failed", "needs_attention"}
        or job.error_code not in SOURCE_DEFECT_CODES
        or not job.checkpoint.get("source_defect")
        or job.requested_by is None
        or job.checkpoint.get("assets_published")
        or source_defect_waits_for_code(job)
    ):
        return None
    try:
        require_processing_manager(job.requested_by)
    except PermissionDenied:
        return None
    expected = job.checkpoint.get(
        "source_revision", job.input.get("command", {}).get("source_revision")
    )
    if (
        job.source_record is None
        or job.source_record.updated_at.isoformat() != expected
    ):
        return None
    choices = available_source_choices(job)
    return next(
        (choice for choice in ("resume_preparation", "retry") if choice in choices),
        None,
    )


@transaction.atomic
def recover_source_defect(identifier):
    snapshot = BackgroundJob.objects.only("requested_by_id").get(pk=identifier)
    if snapshot.requested_by_id is None:
        return None
    actor = User.objects.select_for_update(no_key=True).get(pk=snapshot.requested_by_id)
    job = (
        BackgroundJob.objects.select_for_update(of=("self",))
        .select_related("source_record")
        .get(pk=identifier)
    )
    job.requested_by = actor
    choice = defect_recovery_choice(job)
    if choice is None:
        return None
    retained = dict(job.checkpoint)
    try:
        recovered = resolve_source_job(
            actor, job.pk, {"choice": choice, "expected_updated_at": job.updated_at}
        )
    except (JobStateConflict, PermissionDenied):
        return None
    recovered.checkpoint = {
        **{
            key: value
            for key, value in retained.items()
            if key not in REGENERATED_CHECKPOINT_KEYS
        },
        **recovered.checkpoint,
    }
    for key in REGENERATED_CHECKPOINT_KEYS:
        recovered.checkpoint.pop(key, None)
    recovered.save(update_fields=["checkpoint", "updated_at"])
    defect = retained["source_defect"]
    AuditLog.objects.create(
        actor=actor,
        verb="source.recover_defect",
        target_type=job._meta.label_lower,
        target_id=str(job.pk),
        payload={
            "fingerprint": defect["fingerprint"],
            "previous_version": defect["code_version"],
            "code_version": source_code_version(defect["code_group"]),
        },
    )
    return recovered


def recover_updated_source_defects():
    candidates = BackgroundJob.objects.filter(
        kind="process_source",
        state__in=["failed", "needs_attention"],
        error_code__in=SOURCE_DEFECT_CODES,
        checkpoint__source_defect__fingerprint__isnull=False,
    )
    if not candidates.exists():
        return 0
    for group in set(SOURCE_DEFECT_CODES.values()):
        candidates = candidates.exclude(
            Q(checkpoint__source_defect__code_group=group)
            & Q(checkpoint__source_defect__code_version=source_code_version(group))
        )
    identifiers = list(
        candidates.order_by("created_at", "id").values_list("pk", flat=True)[:50]
    )
    return sum(
        recover_source_defect(identifier) is not None for identifier in identifiers
    )
