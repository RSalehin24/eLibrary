from copy import deepcopy

import pytest
from apps.accounts.models import User
from apps.catalog.editorial.service import EditorialConflict, publish_book
from apps.catalog.models import Book, BookSource
from apps.common.models import AuditLog
from apps.ingestion.source_processing.export_verification import (
    require_verified_exports,
)
from apps.ingestion.source_processing.storage import write_artifact
from apps.ingestion.source_processing.verification import source_verification
from apps.processing.jobs.execution_errors import ExecutionFailure
from rest_framework.test import APIClient
from source_processing_fixtures import curated_source, execute_source_job

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def configured_source(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []


def test_verified_source_publishes_automatically_without_editorial_review(curated_job):
    execute_source_job(curated_job)
    assert curated_job.state == "succeeded"
    assert curated_job.checkpoint["exports_verified"]
    assert curated_job.checkpoint["auto_published"]
    assert curated_job.checkpoint["source_summary"]["verification"]["verified"]
    book = curated_job.book
    assert book.state == "published" and book.editorial_reviewed_at is None
    assert APIClient().get(f"/api/v1/catalog/books/{book.slug}/").status_code == 200
    audit = AuditLog.objects.get(verb="catalog.book.auto_publish")
    assert audit.payload["operation_id"] == str(curated_job.pk)
    client = APIClient()
    client.force_authenticate(curated_job.requested_by)
    detail = client.get(
        f"/api/v1/manage/sources/{curated_job.source_record_id}/"
    ).json()
    assert detail["content_summary"]["verification"]["verified"]
    assert "Missing body content" not in str(detail["content_summary"])


@pytest.mark.parametrize(
    "structure",
    [
        {"topics_expected": 100, "topics_fetched": 99},
        {"source_total_pages": 3, "fetched_total_pages": 2},
        {"toc_incomplete": True},
        {"content_incomplete": True},
    ],
)
def test_any_missing_available_source_content_blocks_publication(
    source_job, tmp_path, structure
):
    result = curated_source(tmp_path)
    result["source_snapshot"]["manifest"] = {"source_structure": structure}
    assert not source_verification(result)["verified"]
    source_job.checkpoint = {"document_ref": write_artifact(source_job.pk, result)}
    source_job.save()
    execute_source_job(source_job)
    assert source_job.state == "needs_attention"
    assert source_job.error_code == "source_content_incomplete"
    assert source_job.book_id is None
    assert not AuditLog.objects.filter(verb="catalog.book.auto_publish").exists()


def test_a_document_without_fetched_source_evidence_is_not_verified(tmp_path):
    result = curated_source(tmp_path)
    result["source_snapshot"]["pages"] = []
    assert not source_verification(result)["verified"]


def test_a_failed_source_page_cannot_be_hidden_by_validated_document_status(tmp_path):
    result = curated_source(tmp_path)
    result["source_snapshot"]["pages"][0]["status_code"] = 503
    assert result["status"] == "validated"
    assert not source_verification(result)["verified"]


def test_export_verification_rejects_a_valid_epub_with_missing_book_text(tmp_path):
    from tests.backend.access.reader_fixtures import write_epub

    result = curated_source(tmp_path)
    html = tmp_path / "book.html"
    html.write_text(result["projection"]["main_content"])
    paths = {"html": html, "epub": write_epub(tmp_path / "different.epub")}
    with pytest.raises(ExecutionFailure) as failure:
        require_verified_exports(result, paths)
    assert failure.value.failure.code == "source_export_content_mismatch"


def test_short_complete_source_text_is_not_rejected_for_its_length(tmp_path):
    result = deepcopy(curated_source(tmp_path))
    assert source_verification(result)["verified"]


def test_extraction_cannot_silently_drop_a_paragraph_of_collected_source(tmp_path):
    result = curated_source(tmp_path)
    section = next(
        section
        for section in result["document"]["sections"]
        if section["section_type"] == "body"
    )
    section["html"] = "<h2>প্রথম অধ্যায়</h2><p>বইয়ের মূল বাংলা লেখা।</p>"
    verification = source_verification(result)
    assert not verification["verified"]
    assert "Collected source text is missing" in " ".join(verification["issues"])


def test_markup_and_unicode_normalization_preserve_source_verification(tmp_path):
    result = curated_source(tmp_path)
    section = next(
        section
        for section in result["document"]["sections"]
        if section["section_type"] == "body"
    )
    section["html"] = (
        section["html"].replace("<p>", "<p>\n <span>").replace("</p>", "</span> </p>")
    )
    assert source_verification(result)["verified"]


def test_publication_recovery_is_idempotent_and_rejects_changed_editions(curated_job):
    from apps.ingestion.source_processing.worker import execute_source_processing
    from apps.processing.jobs.attempts import claim_attempt

    ownership = claim_attempt(curated_job.dispatches.get().pk)
    assert execute_source_processing(ownership)
    assert execute_source_processing(ownership)
    assert AuditLog.objects.filter(verb="catalog.book.auto_publish").count() == 1
    curated_job.refresh_from_db()
    book = curated_job.book
    book.summary = "পরবর্তী সংস্করণের পরিচিতি"
    book.save()
    with pytest.raises(ExecutionFailure) as failure:
        execute_source_processing(ownership)
    assert failure.value.failure.code == "source_catalog_changed"
    assert AuditLog.objects.filter(verb="catalog.book.auto_publish").count() == 1


def test_a_stop_after_preparation_prevents_automatic_publication(
    curated_job, monkeypatch
):
    from apps.ingestion.source_processing.reading_preparation import (
        prepare_source_reading,
    )
    from apps.processing.jobs.controls import request_stop

    def stop_after_preparation(ownership):
        prepared = prepare_source_reading(ownership)
        request_stop(curated_job.pk, "cancel")
        return prepared

    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.prepare_source_reading",
        stop_after_preparation,
    )
    execute_source_job(curated_job)
    assert curated_job.state == "cancelled"
    assert curated_job.book.state != "published"
    assert not AuditLog.objects.filter(verb="catalog.book.auto_publish").exists()


def test_legacy_source_without_verification_cannot_bypass_checks_with_manual_publish():
    actor = User.objects.create_user(
        email="legacy-publisher@example.test", is_staff=True
    )
    book = Book.objects.create(title="আগের উৎসের বই")
    BookSource.objects.create(
        book=book,
        source_url="https://source.test/books/legacy/",
        normalized_source_url="https://source.test/books/legacy/",
    )
    with pytest.raises(EditorialConflict, match="Regenerate"):
        publish_book(actor, book.pk, book.updated_at)
    book.refresh_from_db()
    assert book.state == "draft"


def test_a_manually_added_book_without_a_source_keeps_direct_publication():
    actor = User.objects.create_user(
        email="manual-publisher@example.test", is_staff=True
    )
    book = Book.objects.create(title="নিজের যোগ করা বই", record_type="manual")
    published = publish_book(actor, book.pk, book.updated_at)
    assert published.state == "published"
