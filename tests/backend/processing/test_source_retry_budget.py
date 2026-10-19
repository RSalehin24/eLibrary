import pytest
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.processing.job_models import JobAttempt
from apps.processing.jobs.attempts import claim_attempt
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_explicit_source_retry_renews_a_bounded_budget_without_discarding_history(
    source_job,
):
    ownership = claim_attempt(source_job.dispatches.get().pk)
    source_job.max_attempts = 1
    source_job.save(update_fields=["max_attempts"])
    fail_attempt(
        ownership,
        AttemptFailure(FailureKind.TRANSIENT, "source_storage_unavailable"),
    )
    JobAttempt.objects.bulk_create(
        [
            JobAttempt(
                job=source_job,
                number=number,
                generation=1,
                heartbeat_at=timezone.now(),
                finished_at=timezone.now(),
                error_code="source_storage_unavailable",
            )
            for number in range(2, 11)
        ]
    )
    source_job.attempt_count = 10
    source_job.save(update_fields=["attempt_count", "updated_at"])
    source_job.refresh_from_db()
    resolve_source_job(
        source_job.requested_by,
        source_job.pk,
        {"choice": "retry", "expected_updated_at": source_job.updated_at},
    )
    for expected_state in ["retry_wait", "retry_wait", "failed"]:
        source_job.refresh_from_db()
        source_job.available_at = timezone.now()
        source_job.save(update_fields=["available_at"])
        ownership = claim_attempt(
            source_job.dispatches.get(generation=source_job.generation).pk
        )
        assert ownership is not None
        failed = fail_attempt(
            ownership,
            AttemptFailure(FailureKind.TRANSIENT, "source_storage_unavailable"),
        )
        assert failed.state == expected_state
    assert JobAttempt.objects.count() == 13
    source_job.refresh_from_db()
    assert (
        source_job.max_attempts == 3 and source_job.input["retry_after_attempt"] == 10
    )
