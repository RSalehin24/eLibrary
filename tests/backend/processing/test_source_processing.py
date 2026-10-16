from datetime import timedelta
from uuid import uuid4
from zipfile import ZipFile

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import Book, BookSource, GeneratedAsset, UserBook
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_processing.commands import request_source_processing
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.ingestion.source_processing.storage import write_artifact
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.controls import request_stop, resume_job
from apps.processing.jobs.requests import JobStateConflict
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from source_processing_fixtures import (
    SOURCE_URL,
    TITLE,
    curated_source,
)
from source_processing_fixtures import (
    execute_source_job as execute,
)

pytestmark = pytest.mark.django_db


def test_source_command_is_atomic_idempotent_and_does_not_transfer_ownership(
    source_job,
):
    actor, entry = source_job.requested_by, source_job.source_record
    again = request_source_processing(
        actor, (source_job.pk, entry.pk), entry.updated_at
    )
    assert again.pk == source_job.pk and source_job.dispatches.count() == 1
    with pytest.raises(JobStateConflict):
        request_source_processing(actor, (uuid4(), entry.pk), entry.updated_at)
    assert BackgroundJob.objects.count() == 1 and not UserBook.objects.exists()


def test_source_processing_builds_a_review_draft_with_real_protected_exports(
    curated_job,
):
    execute(curated_job)
    assert curated_job.state == "succeeded"
    book = curated_job.book
    assert book.state == book.review_state == "needs_review"
    assert not book.indexing_eligible and book.editorial_reviewed_at is None
    assert not UserBook.objects.exists()
    assets = list(GeneratedAsset.objects.filter(book=book))
    assert {asset.asset_type for asset in assets} >= {"html", "epub"}
    assert all(
        asset.is_protected and asset.status == "ready" and asset.checksum
        for asset in assets
    )
    assert curated_job.source_record.catalog_book_id == book.pk
    from apps.access.publication_models import PreparedPublication

    assert (
        PreparedPublication.objects.get(checksum=curated_job.asset.checksum).state
        == "ready"
    )
    assert BookSource.objects.get(book=book).normalized_source_url == SOURCE_URL
    with ZipFile(curated_job.asset.file.path) as archive:
        chapter_text = " ".join(
            archive.read(name).decode()
            for name in archive.namelist()
            if name.endswith(".xhtml")
        )
    assert "বইয়ের মূল বাংলা লেখা" in chapter_text
    execute(curated_job)
    assert Book.objects.count() == 1


def test_duplicate_sources_require_a_decision_and_preserve_existing_metadata(
    curated_job,
):
    existing = Book.objects.create(
        title=TITLE, summary="সম্পাদকীয় লেখা", state="published"
    )
    execute(curated_job)
    assert (
        curated_job.state == "needs_attention"
        and curated_job.error_code == "source_duplicate"
    )
    existing.refresh_from_db()
    assert existing.summary == "সম্পাদকীয় লেখা" and existing.state == "published"
    assert Book.objects.count() == 1 and not UserBook.objects.exists()
    assert str(existing.pk) in curated_job.checkpoint["duplicate_book_ids"]


def test_link_resolution_reuses_a_candidate_without_mutating_it_or_ownership(
    curated_job,
):
    existing = Book.objects.create(
        title=TITLE, state="published", summary="অক্ষত পরিচিতি"
    )
    execute(curated_job)
    resolved = resolve_source_job(
        curated_job.requested_by,
        curated_job.pk,
        {
            "choice": "link",
            "book_id": existing.pk,
            "expected_book_updated_at": existing.updated_at,
            "expected_updated_at": curated_job.updated_at,
        },
    )
    assert resolved.state == "succeeded" and resolved.book_id == existing.pk
    existing.refresh_from_db()
    assert existing.summary == "অক্ষত পরিচিতি" and existing.state == "published"
    assert Book.objects.count() == 1 and not UserBook.objects.exists()
    assert (
        SourceCatalogEntry.objects.get(pk=curated_job.source_record_id).catalog_book_id
        == existing.pk
    )


def test_explicit_separate_resolution_creates_a_distinct_review_record(curated_job):
    existing = Book.objects.create(title=TITLE, summary="অক্ষত পরিচিতি")
    execute(curated_job)
    resolve_source_job(
        curated_job.requested_by,
        curated_job.pk,
        {"choice": "separate", "expected_updated_at": curated_job.updated_at},
    )
    curated_job.refresh_from_db()
    execute(curated_job)
    assert curated_job.state == "succeeded" and curated_job.book_id != existing.pk
    existing.refresh_from_db()
    assert existing.summary == "অক্ষত পরিচিতি" and Book.objects.count() == 2


def test_incomplete_sources_require_attention_before_a_book_is_created(
    source_job, tmp_path
):
    result = curated_source(tmp_path)
    result["status"] = "invalid"
    source_job.checkpoint = {"document_ref": write_artifact(source_job.pk, result)}
    source_job.save()
    execute(source_job)
    assert (
        source_job.state == "needs_attention"
        and source_job.error_code == "source_content_incomplete"
    )
    assert not Book.objects.exists()
    resolve_source_job(
        source_job.requested_by,
        source_job.pk,
        {"choice": "retry", "expected_updated_at": source_job.updated_at},
    )
    source_job.refresh_from_db()
    assert source_job.state == "queued" and "document_ref" not in source_job.checkpoint


def test_revision_conflicts_and_unreviewed_targets_do_not_resolve_a_duplicate(
    curated_job,
):
    Book.objects.create(title=TITLE)
    execute(curated_job)
    unrelated = Book.objects.create(title="অন্য বই")
    with pytest.raises(JobStateConflict):
        resolve_source_job(
            curated_job.requested_by,
            curated_job.pk,
            {
                "choice": "link",
                "book_id": unrelated.pk,
                "expected_book_updated_at": unrelated.updated_at,
                "expected_updated_at": curated_job.updated_at,
            },
        )
    with pytest.raises(JobStateConflict):
        resolve_source_job(
            curated_job.requested_by,
            curated_job.pk,
            {
                "choice": "cancel",
                "expected_updated_at": timezone.now() - timedelta(days=1),
            },
        )


def test_revoked_source_authority_prevents_worker_side_effects(curated_job):
    actor = curated_job.requested_by
    actor.is_staff = False
    actor.save()
    execute(curated_job)
    assert (
        curated_job.state == "failed" and curated_job.error_code == "permission_revoked"
    )
    assert not Book.objects.exists()


def test_pause_before_export_publication_can_resume_without_another_book(
    curated_job, monkeypatch
):
    from apps.ingestion.source_processing.exports import generated_source_assets

    def pause_after_exports(ownership, result):
        paths = generated_source_assets(ownership, result)
        request_stop(curated_job.pk, "pause")
        return paths

    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.generated_source_assets",
        pause_after_exports,
    )
    execute(curated_job)
    assert curated_job.state == "paused" and Book.objects.count() == 1
    assert not GeneratedAsset.objects.exists()
    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.generated_source_assets",
        generated_source_assets,
    )
    resume_job(curated_job.pk)
    curated_job.refresh_from_db()
    execute(curated_job)
    assert curated_job.state == "succeeded" and Book.objects.count() == 1


def test_source_operations_enforce_csrf_and_exclude_raw_state(source_job):
    client = Client(enforce_csrf_checks=True)
    client.force_login(source_job.requested_by)
    entry = source_job.source_record
    url = f"/api/v1/manage/sources/{entry.pk}/process/"
    values = {
        "operation_id": str(source_job.pk),
        "expected_updated_at": entry.updated_at.isoformat(),
    }
    assert client.post(url, values, content_type="application/json").status_code == 403
    csrf = client.get("/api/v1/auth/session/").json()["csrf_token"]
    accepted = client.post(
        url, values, content_type="application/json", HTTP_X_CSRFTOKEN=csrf
    )
    assert accepted.status_code == 202
    detail = client.get(accepted.json()["status_url"])
    assert detail.json()["source_record"] == {"id": str(entry.pk), "title": TITLE}
    assert "input" not in detail.json() and "checkpoint" not in detail.json()
    assert (
        detail["Cache-Control"] == "private, no-store"
        and detail["X-Robots-Tag"] == "noindex"
    )


def test_source_job_reads_do_not_load_book_bodies_or_source_payloads(
    curated_job, client
):
    execute(curated_job)
    client.force_login(curated_job.requested_by)
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/v1/manage/jobs/")
    assert response.status_code == 200
    sql = " ".join(query["sql"] for query in queries.captured_queries)
    assert "main_content_html" not in sql and "raw_data" not in sql


def test_readers_and_metadata_only_accounts_cannot_process_or_resolve_sources(
    source_job, client
):
    actor = User.objects.create_user(email="source-denied@library.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.METADATA_EDIT)
    client.force_login(actor)
    assert (
        client.post(
            f"/api/v1/manage/sources/{source_job.source_record_id}/process/",
            {},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/manage/jobs/{source_job.pk}/source-issue/").status_code
        == 403
    )
