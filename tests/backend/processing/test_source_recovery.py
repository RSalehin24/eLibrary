from unittest.mock import Mock

import pytest
from apps.catalog.editorial.service import (
    EditorialConflict,
    publish_book,
    review_book_editorial,
)
from apps.catalog.models import Book, BookSource, GeneratedAsset
from apps.ingestion.source_processing.exports import generated_source_assets
from apps.ingestion.source_processing.issues import source_issue
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.processing.jobs.controls import request_stop, resume_job
from apps.processing.jobs.requests import JobStateConflict
from source_processing_fixtures import TITLE
from source_processing_fixtures import execute_source_job as execute

pytestmark = pytest.mark.django_db


def failed_export(job, monkeypatch):
    monkeypatch.setattr(
        "apps.ingestion.source_processing.exports.generate_exports",
        Mock(side_effect=OSError("fixture storage unavailable")),
    )
    job.max_attempts = 1
    job.save()
    execute(job)
    assert job.state == "failed" and job.book_id and not GeneratedAsset.objects.exists()


def test_failed_exports_resume_the_existing_draft_and_checkpoint(
    curated_job, monkeypatch
):
    from apps.ingestion.source_processing.exports import generate_exports

    failed_export(curated_job, monkeypatch)
    checkpoint = dict(curated_job.checkpoint)
    assert source_issue(curated_job.pk)["available_choices"] == [
        "resume_preparation",
        "cancel",
    ]
    resolve_source_job(
        curated_job.requested_by,
        curated_job.pk,
        {"choice": "resume_preparation", "expected_updated_at": curated_job.updated_at},
    )
    monkeypatch.setattr(
        "apps.ingestion.source_processing.exports.generate_exports", generate_exports
    )
    curated_job.refresh_from_db()
    assert curated_job.checkpoint == checkpoint
    execute(curated_job)
    assert curated_job.state == "succeeded" and Book.objects.count() == 1
    assert curated_job.asset.file.name and not curated_job.asset.legacy_path


def test_resume_reuses_generated_exports_after_pause(curated_job, monkeypatch):
    def pause(ownership, result):
        paths = generated_source_assets(ownership, result)
        request_stop(curated_job.pk, "pause")
        return paths

    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.generated_source_assets", pause
    )
    execute(curated_job)
    assert curated_job.state == "paused" and curated_job.checkpoint["exports_ref"]
    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.generated_source_assets",
        generated_source_assets,
    )
    generator = Mock(side_effect=AssertionError("A completed export must be reused"))
    monkeypatch.setattr(
        "apps.ingestion.source_processing.exports.generate_exports", generator
    )
    resume_job(curated_job.pk)
    curated_job.refresh_from_db()
    execute(curated_job)
    assert curated_job.state == "succeeded"
    generator.assert_not_called()


@pytest.mark.parametrize("changed", ["source", "book", "permission"])
def test_changed_authority_or_input_prevents_asset_publication(
    curated_job, monkeypatch, changed
):
    def change_after_exports(ownership, result):
        paths = generated_source_assets(ownership, result)
        curated_job.refresh_from_db()
        if changed == "book":
            book = curated_job.book
            book.summary = "সম্পাদকের নতুন পরিচিতি"
            book.save()
        elif changed == "source":
            entry = curated_job.source_record
            entry.title = "পরিবর্তিত উৎস"
            entry.save()
        else:
            actor = curated_job.requested_by
            actor.is_staff = False
            actor.save()
        return paths

    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.generated_source_assets",
        change_after_exports,
    )
    execute(curated_job)
    assert curated_job.state in {"failed", "needs_attention"}
    assert (
        curated_job.error_code
        == {
            "source": "source_record_changed",
            "book": "source_catalog_changed",
            "permission": "permission_revoked",
        }[changed]
    )
    assert not GeneratedAsset.objects.exists() and Book.objects.count() == 1


def test_failed_draft_cannot_be_retried_as_a_second_book_or_resumed_after_edits(
    curated_job, monkeypatch
):
    failed_export(curated_job, monkeypatch)
    with pytest.raises(JobStateConflict):
        resolve_source_job(
            curated_job.requested_by,
            curated_job.pk,
            {"choice": "retry", "expected_updated_at": curated_job.updated_at},
        )
    book = curated_job.book
    book.summary = "সম্পাদকীয় পরিবর্তন"
    book.save()
    assert source_issue(curated_job.pk)["available_choices"] == ["cancel"]
    with pytest.raises(JobStateConflict):
        resolve_source_job(
            curated_job.requested_by,
            curated_job.pk,
            {
                "choice": "resume_preparation",
                "expected_updated_at": curated_job.updated_at,
            },
        )
    assert Book.objects.count() == 1


def test_reviewed_source_draft_cannot_be_published_with_unfinished_exports(
    curated_job, monkeypatch
):
    failed_export(curated_job, monkeypatch)
    book = review_book_editorial(
        curated_job.requested_by, curated_job.book_id, curated_job.book.updated_at
    )
    with pytest.raises(EditorialConflict):
        publish_book(curated_job.requested_by, book.pk, book.updated_at)
    resolve_source_job(
        curated_job.requested_by,
        curated_job.pk,
        {"choice": "cancel", "expected_updated_at": curated_job.updated_at},
    )
    with pytest.raises(EditorialConflict):
        publish_book(curated_job.requested_by, book.pk, book.updated_at)


def test_duplicate_link_checks_the_selected_book_revision(curated_job):
    candidate = Book.objects.create(title=TITLE)
    execute(curated_job)
    previous = candidate.updated_at
    candidate.summary = "সম্পাদকের সর্বশেষ লেখা"
    candidate.save()
    with pytest.raises(JobStateConflict):
        resolve_source_job(
            curated_job.requested_by,
            curated_job.pk,
            {
                "choice": "link",
                "book_id": candidate.pk,
                "expected_book_updated_at": previous,
                "expected_updated_at": curated_job.updated_at,
            },
        )
    assert not BookSource.objects.exists() and curated_job.state == "needs_attention"


def test_existing_source_link_is_never_reassigned_by_a_worker(curated_job):
    existing = Book.objects.create(title="আগের বই")
    BookSource.objects.create(
        book=existing,
        source_url=curated_job.source_record.source_url,
        normalized_source_url=curated_job.source_record.source_url,
    )
    execute(curated_job)
    assert (
        curated_job.state == "needs_attention"
        and curated_job.error_code == "source_already_linked"
    )
    assert BookSource.objects.get().book_id == existing.pk and Book.objects.count() == 1


def test_late_cancellation_preserves_previous_assets(
    curated_job, monkeypatch, tmp_path
):
    from apps.ingestion.source_processing.asset_publication import stored_source_assets

    previous = tmp_path / "previous.epub"
    previous.write_bytes(b"previous valid asset fixture")

    def cancel_after_staging(ownership, paths):
        stored = stored_source_assets(ownership, paths)
        curated_job.refresh_from_db()
        GeneratedAsset.objects.create(
            book=curated_job.book,
            asset_type="epub",
            status="ready",
            legacy_path=str(previous),
            checksum="previous-checksum",
        )
        request_stop(curated_job.pk, "cancel")
        return stored

    monkeypatch.setattr(
        "apps.ingestion.source_processing.asset_publication.stored_source_assets",
        cancel_after_staging,
    )
    execute(curated_job)
    assert curated_job.state == "cancelled"
    asset = GeneratedAsset.objects.get()
    assert asset.legacy_path == str(previous) and asset.checksum == "previous-checksum"
    assert previous.read_bytes() == b"previous valid asset fixture"
