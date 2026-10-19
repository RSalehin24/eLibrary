from datetime import timedelta

import pytest
from apps.catalog.content_quality import book_is_quarantined, quarantine_book
from apps.catalog.discovery.publication import public_books
from apps.catalog.models import Book
from apps.common.permissions import (
    user_can_download_book_assets,
    user_can_send_to_kindle,
    user_can_view_preview_html,
    user_has_reader_access,
)
from apps.ingestion.models import SourceEdition
from apps.ingestion.source_processing.classification import inline_classification
from apps.processing.jobs.failures import FailureKind
from django.utils import timezone
from source_processing_fixtures import execute_source_job

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        (
            "<h2>A Midsummer Night’s Dream</h2><p>A Midsummer Night’s Dream is a romantic comedy by William Shakespeare, written around 1594.</p>",
            "description_only",
        ),
        ("<h2>প্রথম অধ্যায়</h2><p>আজ সকালবেলা দরজায় এসে দাঁড়াল সে।</p>", "inline_reading"),
        ('<div class="poem"><p>মেঘের কোলে রোদ হেসেছে।</p></div>', "inline_reading"),
        ("<p>one<br>two<br>three<br>four</p>", "inline_reading"),
        ("<p>Buy this book.</p>", "unknown_layout"),
        ("<p></p>", "unavailable_content"),
    ],
)
def test_source_classification_requires_reading_evidence(html, expected):
    assert inline_classification(html) == expected


def test_quarantine_preserves_book_and_denies_every_reading_action(curated_job):
    execute_source_job(curated_job)
    book, actor = curated_job.book, curated_job.requested_by
    assets = list(book.generated_assets.values_list("pk", flat=True))
    quarantined = quarantine_book(book, {"reason": "description_only"}, actor=actor)
    assert book_is_quarantined(quarantined)
    assert not public_books().filter(pk=book.pk).exists()
    for permitted in (
        user_has_reader_access,
        user_can_download_book_assets,
        user_can_send_to_kindle,
        user_can_view_preview_html,
    ):
        assert not permitted(actor, quarantined)
    assert list(book.generated_assets.values_list("pk", flat=True)) == assets
    assert Book.objects.filter(pk=book.pk, deleted_at__isnull=True).exists()


def test_published_edition_records_validator_and_files(curated_job):
    execute_source_job(curated_job)
    edition = SourceEdition.objects.get(operation=curated_job)
    assert edition.state == "published" and edition.book_id == curated_job.book_id
    assert edition.validator_version == 2 and edition.validation_report["verified"]
    assert {"html", "epub"} <= edition.asset_manifest.keys()
    assert edition.document_reference


def test_failed_new_reader_preparation_preserves_current_publication(
    regeneration, tmp_path, monkeypatch
):
    from pathlib import Path

    from apps.processing.jobs.execution_errors import ExecutionFailure
    from regeneration_fixtures import request_regeneration
    from source_processing_fixtures import curated_source

    actor, book, _, asset, _ = regeneration
    previous_text, previous_file = book.main_content_html, asset.legacy_path
    job = request_regeneration(regeneration)
    book.refresh_from_db()
    assert book.state == "published"
    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.curate_source_job",
        lambda ownership, current: (curated_source(tmp_path), current.checkpoint),
    )

    def unavailable(asset):
        raise ExecutionFailure(FailureKind.TRANSIENT, "storage_unavailable")

    monkeypatch.setattr(
        "apps.ingestion.source_processing.reading_preparation.prepare_checked_asset",
        unavailable,
    )
    execute_source_job(job)
    book.refresh_from_db()
    asset.refresh_from_db()
    assert job.state == "retry_wait"
    assert book.state == "published" and book.main_content_html == previous_text
    assert asset.legacy_path == previous_file and Path(previous_file).exists()
    assert user_has_reader_access(actor, book)
    assert not job.checkpoint.get("content_committed")
    assert not job.checkpoint.get("assets_published")


def test_audit_hides_description_and_schedules_idempotent_automatic_repair(curated_job):
    from apps.catalog.models import UserBook
    from apps.ingestion.source_processing.audit import audit_source_publication
    from apps.ingestion.source_processing.documents import (
        read_source_result,
        write_source_result,
    )
    from apps.processing.job_models import BackgroundJob

    execute_source_job(curated_job)
    UserBook.objects.create(user=curated_job.requested_by, book=curated_job.book)
    result = read_source_result(curated_job.pk, curated_job.checkpoint["document_ref"])
    result["source_snapshot"]["raw_scrape_payload"].update(
        content_items=[], main_content="<p>This is a novel written in 1900.</p>"
    )
    curated_job.checkpoint["document_ref"] = write_source_result(curated_job.pk, result)
    curated_job.save()
    report = audit_source_publication(curated_job, apply=True)
    assert not report["verified"] and report["classification"] == "description_only"
    curated_job.book.refresh_from_db()
    assert curated_job.book.source_quality_state == "quarantined"
    repair = BackgroundJob.objects.get(pk=report["repair_operation_id"])
    assert (
        repair.state == "retry_wait" and repair.error_code == "source_description_only"
    )
    assert repair.available_at > timezone.now() + timedelta(hours=5)
    assert audit_source_publication(curated_job, apply=True)[
        "repair_operation_id"
    ] == str(repair.pk)
    assert UserBook.objects.filter(book=curated_job.book).count() == 1


def test_one_unavailable_chapter_waits_for_source_without_publishing_partial_book(
    source_job, tmp_path
):
    from apps.ingestion.source_processing.documents import write_source_result
    from source_processing_fixtures import curated_source

    result = curated_source(tmp_path)
    result["source_snapshot"]["raw_scrape_payload"]["content_items"].append(
        {"url": "https://source.test/lessons/unavailable/", "has_content": None}
    )
    source_job.checkpoint = {"document_ref": write_source_result(source_job.pk, result)}
    source_job.save()
    execute_source_job(source_job)
    assert (
        source_job.state == "retry_wait"
        and source_job.error_code == "source_content_unavailable"
    )
    assert source_job.book_id is None and "document_ref" not in source_job.checkpoint
    assert not Book.objects.exists()
