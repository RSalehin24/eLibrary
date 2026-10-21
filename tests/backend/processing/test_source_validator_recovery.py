from datetime import timedelta

import pytest
from apps.common.models import AuditLog
from apps.ingestion.models import SourceEdition
from apps.ingestion.source_processing.classification import VALIDATOR_VERSION
from apps.ingestion.source_processing.documents import (
    read_source_result,
    write_source_result,
)
from apps.ingestion.source_processing.validator_recovery import (
    recover_source_validator,
    recover_updated_source_validation,
)
from apps.processing.jobs.attempts import claim_attempt
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from apps.processing.jobs.source_dispatch import work_lane
from django.utils import timezone

pytestmark = pytest.mark.django_db


def old_validation_wait(job):
    SourceEdition.objects.create(
        operation=job,
        source=job.source_record,
        validator_version=2,
        document_reference=job.checkpoint["document_ref"],
        classification="unknown_layout",
    )
    ownership = claim_attempt(job.dispatches.get(generation=job.generation).pk)
    fail_attempt(
        ownership, AttemptFailure(FailureKind.TRANSIENT, "source_layout_unknown")
    )
    job.refresh_from_db()
    return job


def test_updated_validator_requeues_a_retained_complete_book_once_without_erasing_attempts(
    curated_job,
):
    job = old_validation_wait(curated_job)
    previous_generation, previous_attempts = job.generation, job.attempt_count
    recovered = recover_source_validator(job.pk)
    assert recovered.state == "queued" and recovered.error_code == ""
    assert recovered.generation == previous_generation + 1
    assert (
        recovered.attempt_count == previous_attempts and recovered.attempts.count() == 1
    )
    assert recovered.available_at <= timezone.now()
    assert (
        recovered.checkpoint["source_validation_recovery"]["validator_version"]
        == VALIDATOR_VERSION
    )
    assert "document_ref" not in recovered.checkpoint
    assert work_lane(recovered) == "recovery"
    assert recover_source_validator(job.pk) is None
    assert recover_updated_source_validation() == 0
    assert (
        AuditLog.objects.filter(
            verb="source.recover_validation", target_id=str(job.pk)
        ).count()
        == 1
    )


def test_a_synopsis_is_not_requeued_merely_because_the_validator_version_changed(
    curated_job,
):
    result = read_source_result(curated_job.pk, curated_job.checkpoint["document_ref"])
    result["source_snapshot"]["raw_scrape_payload"].update(
        content_items=[], main_content="<p>This is a novel written in 1900.</p>"
    )
    result["document"]["sections"] = []
    curated_job.checkpoint["document_ref"] = write_source_result(curated_job.pk, result)
    curated_job.save()
    job = old_validation_wait(curated_job)
    assert recover_source_validator(job.pk) is None
    job.refresh_from_db()
    assert job.state == "retry_wait" and job.available_at > timezone.now() + timedelta(
        hours=5
    )


def test_validator_recovery_receives_a_dispatch_turn_ahead_of_older_new_work(
    curated_job, settings
):
    from uuid import uuid4

    from apps.ingestion.models import SourceCatalogEntry
    from apps.processing.job_models import BackgroundJob, JobDispatch
    from apps.processing.jobs.dispatches import claim_dispatches

    settings.CELERY_PROCESSING_CONCURRENCY = 1
    recovered = recover_source_validator(old_validation_wait(curated_job).pk)
    for _ in range(3):
        entry = SourceCatalogEntry.objects.create(
            source_url=f"https://source.test/books/{uuid4()}/", title="Older book"
        )
        older = BackgroundJob.objects.create(
            kind="process_source",
            requested_by=recovered.requested_by,
            source_record=entry,
            available_at=timezone.now() - timedelta(days=1),
        )
        JobDispatch.objects.create(
            job=older, generation=older.generation, available_at=older.available_at
        )
    selected = [
        JobDispatch.objects.get(pk=lease.identifier).job for lease in claim_dispatches()
    ]
    assert len(selected) == 2
    assert recovered.pk in {job.pk for job in selected}
    assert {work_lane(job) for job in selected} == {"new", "recovery"}


@pytest.mark.parametrize(
    "change",
    ["paused", "cancelled", "source_changed", "permission_revoked", "already_current"],
)
def test_validator_recovery_honors_authority_current_source_and_explicit_stop(
    curated_job, change
):
    job = old_validation_wait(curated_job)
    if change in {"paused", "cancelled"}:
        job.state = change
        job.save()
    elif change == "source_changed":
        job.source_record.title = "পরিবর্তিত বই"
        job.source_record.save()
    elif change == "permission_revoked":
        job.requested_by.is_staff = False
        job.requested_by.save()
    else:
        job.source_edition.validator_version = VALIDATOR_VERSION
        job.source_edition.save()
    generation = job.generation
    assert recover_source_validator(job.pk) is None
    job.refresh_from_db()
    assert job.generation == generation


@pytest.mark.parametrize(
    "failure", ["source_description_only", "source_content_unavailable"]
)
def test_a_recollected_book_keeps_its_six_hour_wait_when_a_component_remains_unavailable(
    curated_job, failure
):
    job = old_validation_wait(curated_job)
    recovered = recover_source_validator(job.pk)
    owned = claim_attempt(recovered.dispatches.get(generation=recovered.generation).pk)
    fail_attempt(owned, AttemptFailure(FailureKind.TRANSIENT, failure))
    recovered.refresh_from_db()
    assert recovered.state == "retry_wait"
    assert recovered.available_at > timezone.now() + timedelta(hours=5)
    assert (
        recovered.checkpoint["source_validation_recovery"]["validator_version"]
        == VALIDATOR_VERSION
    )
    assert recover_source_validator(job.pk) is None
