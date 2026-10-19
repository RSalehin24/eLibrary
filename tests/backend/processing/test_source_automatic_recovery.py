import pytest
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_processing.recovery import (
    complete_pending_source,
    restart_repaired_source,
)
from apps.ingestion.source_processing.storage import read_artifact, write_artifact
from apps.ingestion.source_processing.worker import require_complete_source
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.attempts import claim_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import fail_attempt
from apps.processing.jobs.requests import JobStateConflict
from django.utils import timezone
from source_processing_fixtures import execute_source_job

pytestmark = pytest.mark.django_db


def test_queued_source_details_explain_how_many_books_were_queued_earlier(
    source_job, client
):
    entry = SourceCatalogEntry.objects.create(
        source_url="https://source.test/books/second/", title="Second"
    )
    second = BackgroundJob.objects.create(
        kind="process_source",
        source_record=entry,
        requested_by=source_job.requested_by,
        available_at=timezone.now(),
    )
    client.force_login(source_job.requested_by)
    response = client.get(f"/api/v1/manage/jobs/{second.pk}/")
    assert response.status_code == 200 and response.json()["queue_ahead"] == 1
    assert (
        client.get(f"/api/v1/manage/jobs/{source_job.pk}/").json()["queue_ahead"] == 0
    )


def test_application_repairs_refresh_the_landing_page_and_keep_completed_chapter_fetches(
    source_job,
):
    url = source_job.source_record.source_url
    pages = {
        url: write_artifact(source_job.pk, "Old contents nonce"),
        "https://source.test/lessons/first/": write_artifact(
            source_job.pk, "Complete chapter text"
        ),
    }
    source_job.state, source_job.error_code = "failed", "source_url_not_allowed"
    source_job.checkpoint = {
        "page_cache_ref": write_artifact(source_job.pk, pages),
        "document_ref": "old",
    }
    source_job.save()
    repaired = restart_repaired_source(source_job.requested_by, source_job.pk)
    assert repaired.state == "queued" and "document_ref" not in repaired.checkpoint
    retained = read_artifact(repaired.pk, repaired.checkpoint["page_cache_ref"])
    assert url not in retained and list(retained) == [
        "https://source.test/lessons/first/"
    ]
    assert repaired.checkpoint["cache_bytes"] == len("Complete chapter text")


def test_old_completed_preparation_continues_through_normal_checks(
    curated_job, monkeypatch
):
    from apps.ingestion.source_processing import worker

    publish = worker.publish_verified_source
    monkeypatch.setattr(worker, "publish_verified_source", lambda _: True)
    execute_source_job(curated_job)
    assert curated_job.state == "succeeded" and curated_job.book.state == "processing"
    complete_pending_source(curated_job.requested_by, curated_job.pk)
    assert (
        complete_pending_source(curated_job.requested_by, curated_job.pk).generation
        == 2
    )
    monkeypatch.setattr(worker, "publish_verified_source", publish)
    curated_job.refresh_from_db()
    execute_source_job(curated_job)
    assert curated_job.state == "succeeded" and curated_job.checkpoint["auto_published"]
    assert curated_job.book.state == "published"
    with pytest.raises(JobStateConflict):
        complete_pending_source(curated_job.requested_by, curated_job.pk)


@pytest.mark.parametrize("content_items", [[{"has_content": None, "content": ""}], []])
def test_source_empty_chapters_are_rechecked_without_manual_decisions(
    source_job, content_items
):
    result = {
        "projection": {"book_title": "Book"},
        "source_snapshot": {
            "raw_scrape_payload": {
                "main_content": "",
                "content_items": content_items,
            }
        },
    }
    with pytest.raises(ExecutionFailure) as error:
        require_complete_source(result)
    assert error.value.failure.code == "source_content_unavailable"
    source_job.max_attempts = 1
    source_job.checkpoint = {
        "document_ref": "old",
        "page_cache_ref": "old",
        "source_revision": source_job.source_record.updated_at.isoformat(),
    }
    source_job.save()
    ownership = claim_attempt(source_job.dispatches.get().pk)
    fail_attempt(ownership, error.value.failure)
    source_job.refresh_from_db()
    assert source_job.state == "retry_wait" and source_job.available_at > timezone.now()
    assert source_job.error_code == "source_content_unavailable"
    assert (
        "document_ref" not in source_job.checkpoint
        and "page_cache_ref" not in source_job.checkpoint
    )
    source_job.available_at = timezone.now()
    source_job.save(update_fields=["available_at"])
    assert (
        claim_attempt(source_job.dispatches.get(generation=source_job.generation).pk)
        is not None
    )
