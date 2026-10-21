import pytest
from apps.ingestion.source_processing.audit import audit_source_publication
from apps.ingestion.source_processing.documents import (
    read_source_result,
    write_source_result,
)
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.source_dispatch import work_lane
from django.utils import timezone
from source_processing_fixtures import execute_source_job

pytestmark = pytest.mark.django_db


def test_a_published_collection_with_only_an_introduction_is_quarantined_and_rebuilt_without_a_source_wait(
    curated_job,
):
    execute_source_job(curated_job)
    assets = set(curated_job.book.generated_assets.values_list("pk", flat=True))
    result = read_source_result(curated_job.pk, curated_job.checkpoint["document_ref"])
    result["source_snapshot"]["raw_scrape_payload"].update(
        content_items=[],
        main_content='<p>এই সংকলনের পরিচিতি।</p><h2>সূচি</h2><ul><li><a href="https://source.test/books/first/">প্রথম বই</a></li><li><a href="https://source.test/books/second/">দ্বিতীয় বই</a></li></ul>',
    )
    curated_job.checkpoint["document_ref"] = write_source_result(curated_job.pk, result)
    curated_job.save()
    report = audit_source_publication(curated_job, apply=True)
    assert report["classification"] == "linked_collection" and not report["verified"]
    curated_job.book.refresh_from_db()
    assert curated_job.book.source_quality_state == "quarantined"
    assert set(curated_job.book.generated_assets.values_list("pk", flat=True)) == assets
    repair = BackgroundJob.objects.get(pk=report["repair_operation_id"])
    assert repair.state == "queued" and repair.available_at <= timezone.now()
    assert work_lane(repair) == "recovery"
    assert audit_source_publication(curated_job, apply=True)[
        "repair_operation_id"
    ] == str(repair.pk)
