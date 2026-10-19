from copy import deepcopy

import pytest
from apps.ingestion.source_processing.storage import write_artifact
from apps.ingestion.source_processing.validation_recovery import (
    recover_source_validation,
)
from apps.processing.job_models import BackgroundJob
from django.utils import timezone
from source_processing_fixtures import curated_source

pytestmark = pytest.mark.django_db


def held_result(job, result):
    job.state, job.error_code = "needs_attention", "source_content_incomplete"
    job.checkpoint = {"document_ref": write_artifact(job.pk, result)}
    job.save()


def test_current_validation_requeues_a_book_without_reusing_old_invalid_document(
    source_job, tmp_path
):
    result = curated_source(tmp_path)
    result["status"] = "review_required"
    result["validation"]["errors"] = ["Old validator rejected narrative login prose."]
    held_result(source_job, result)
    repaired = recover_source_validation(source_job.pk)
    assert repaired.state == "queued" and repaired.generation == 2
    assert "document_ref" not in repaired.checkpoint
    assert recover_source_validation(source_job.pk) is None
    assert BackgroundJob.objects.count() == 1


def test_empty_inline_source_is_scheduled_for_recheck_without_creating_a_book(
    source_job, tmp_path
):
    result = curated_source(tmp_path)
    result["source_snapshot"]["raw_scrape_payload"]["main_content"] = ""
    held_result(source_job, result)
    repaired = recover_source_validation(source_job.pk)
    assert repaired.state == "retry_wait" and repaired.book_id is None
    assert repaired.error_code == "source_content_unavailable"
    assert (repaired.available_at - timezone.now()).total_seconds() > 5 * 3600
    assert repaired.dispatches.get(generation=2).available_at == repaired.available_at


def test_unresolved_incomplete_source_is_not_published_or_retried_as_a_verified_book(
    source_job, tmp_path
):
    result = curated_source(tmp_path)
    result["source_snapshot"]["manifest"] = {
        "source_structure": {"topics_expected": 4, "topics_fetched": 2}
    }
    held_result(source_job, result)
    original = deepcopy(source_job.checkpoint)
    assert recover_source_validation(source_job.pk) is None
    source_job.refresh_from_db()
    assert source_job.state == "needs_attention" and source_job.checkpoint == original
