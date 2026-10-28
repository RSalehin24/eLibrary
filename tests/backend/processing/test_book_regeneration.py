from pathlib import Path
from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.catalog.models import (
    Book,
    BookSource,
    GeneratedAsset,
    MetadataVersion,
)
from apps.ingestion.source_processing.issues import available_source_choices
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from regeneration_fixtures import request_regeneration
from rest_framework.test import APIClient
from source_processing_fixtures import curated_source, execute_source_job

pytestmark = pytest.mark.django_db


def test_regeneration_reuses_the_book_and_preserves_previous_files_sessions_and_metadata(
    regeneration, tmp_path, monkeypatch
):
    actor, book, _, asset, publication = regeneration
    client = APIClient()
    client.force_authenticate(actor)
    session = client.post(f"/api/v1/reading/books/{book.slug}/launch/").json()
    original = Path(asset.legacy_path)
    job = request_regeneration(regeneration)
    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.curate_source_job",
        lambda ownership, current: (curated_source(tmp_path), current.checkpoint),
    )
    execute_source_job(job)
    assert job.state == "succeeded", job.error_code
    book.refresh_from_db()
    asset.refresh_from_db()
    assert Book.objects.count() == 1 and original.exists() and asset.file.size > 0
    assert (
        book.title == "সম্পাদিত বইয়ের নাম"
        and book.summary == "সম্পাদিত পরিচিতি"
        and book.seo_title == "Edited SEO"
    )
    assert list(book.contributors.values_list("name", flat=True)) == ["সম্পাদিত লেখক"]
    assert book.state == "published" and (not hasattr(book, "editorial_reviewed_at"))
    assert "বাংলা লেখা" in book.main_content_html
    assert (
        MetadataVersion.objects.get(book=book, source="before_regeneration").snapshot[
            "main_content_html"
        ]
        == "<p>Previous text</p>"
    )
    assert book.curated_documents.count() == 1
    old_session = client.get(f"/api/v1/reading/sessions/{session['id']}/").json()
    assert old_session["chapters"] == publication.manifest["chapters"]
    with GeneratedAsset.objects.get(book=book, asset_type="html").file.open(
        "rb"
    ) as handle:
        html = handle.read().decode()
    assert book.title in html and "সম্পাদিত লেখক" in html


def test_regeneration_api_is_revision_checked_idempotent_and_private(regeneration):
    actor, book, _, _, _ = regeneration
    client = APIClient()
    client.force_authenticate(actor)
    path = f"/api/v1/manage/books/{book.slug}/regenerate/"
    values = {
        "operation_id": str(uuid4()),
        "expected_updated_at": book.updated_at.isoformat(),
    }
    first = client.post(path, values, format="json")
    assert first.status_code == 202 and first["Cache-Control"] == "private, no-store"
    assert first.json()["book"]["state"] == "published"
    assert (
        client.post(path, values, format="json").json()["operation_id"]
        == first.json()["operation_id"]
    )
    assert BackgroundJob.objects.filter(input__regenerate_book=True).count() == 1
    book.refresh_from_db()
    assert (
        client.post(
            path,
            {
                **values,
                "operation_id": str(uuid4()),
                "expected_updated_at": book.updated_at.isoformat(),
            },
            format="json",
        ).status_code
        == 409
    )


def test_reader_updates_cannot_overlap_a_regeneration(regeneration):
    actor, book, _, asset, _ = regeneration
    job = request_regeneration(regeneration)
    from apps.processing.jobs.requests import (
        JobStateConflict,
        PreparationRequest,
        request_preparation,
    )
    from apps.processing.managed_assets import processing_assets

    with pytest.raises(JobStateConflict):
        request_preparation(
            actor, PreparationRequest(uuid4(), asset.pk, asset.updated_at)
        )
    info = next(item for item in processing_assets(book, actor) if item.pk == asset.pk)
    assert info.active_preparation_id == job.pk
    assert not BackgroundJob.objects.filter(book=book, kind="prepare_epub").exists()


def test_regeneration_needs_both_metadata_and_processing_authority(regeneration):
    actor, book, _, _, _ = regeneration
    actor.is_staff = False
    actor.save()
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    client = APIClient()
    client.force_authenticate(actor)
    path = f"/api/v1/manage/books/{book.slug}/"
    assert client.get(path + "controls/").status_code == 404
    assert (
        client.post(
            path + "regenerate/",
            {
                "operation_id": str(uuid4()),
                "expected_updated_at": book.updated_at.isoformat(),
            },
            format="json",
        ).status_code
        == 404
    )
    PermissionGrant.objects.filter(user=actor).delete()
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.PROCESSING_MANAGE)
    assert client.get(path + "controls/").status_code == 404
    assert client.post(path + "regenerate/", {}, format="json").status_code == 404


def test_metadata_changes_during_regeneration_prevent_replacement(regeneration):
    _, book, _, asset, _ = regeneration
    job = request_regeneration(regeneration)
    original = asset.legacy_path
    book.refresh_from_db()
    book.title = "Changed while fetching"
    book.save()
    execute_source_job(job)
    asset.refresh_from_db()
    assert job.state == "needs_attention" and job.error_code == "source_catalog_changed"
    assert asset.legacy_path == original and not asset.file.name
    assert available_source_choices(job) == ["cancel"]


def test_failed_fetch_can_be_explicitly_retried_without_losing_previous_files(
    regeneration, monkeypatch
):
    actor, _, _, asset, _ = regeneration
    job = request_regeneration(regeneration)

    def unavailable(*arguments):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_request_rejected")

    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.curate_source_job", unavailable
    )
    execute_source_job(job)
    assert job.state == "failed" and available_source_choices(job) == [
        "retry",
        "cancel",
    ]
    revision = job.checkpoint["catalog_revision"]
    resolve_source_job(
        actor, job.pk, {"expected_updated_at": job.updated_at, "choice": "retry"}
    )
    job.refresh_from_db()
    assert job.state == "queued" and job.checkpoint["catalog_revision"] == revision
    assert Path(asset.legacy_path).exists()


def test_invalid_source_and_stale_commands_change_nothing(regeneration):
    actor, book, _, _, _ = regeneration
    client = APIClient()
    client.force_authenticate(actor)
    path = f"/api/v1/manage/books/{book.slug}/regenerate/"
    assert (
        client.post(
            path,
            {
                "operation_id": str(uuid4()),
                "expected_updated_at": "2000-01-01T00:00:00Z",
            },
            format="json",
        ).status_code
        == 409
    )
    BookSource.objects.filter(book=book).update(
        normalized_source_url="https://other.test/book/"
    )
    assert (
        client.post(
            path,
            {
                "operation_id": str(uuid4()),
                "expected_updated_at": book.updated_at.isoformat(),
            },
            format="json",
        ).status_code
        == 400
    )
    book.refresh_from_db()
    assert (
        book.state == "published"
        and not BackgroundJob.objects.filter(input__regenerate_book=True).exists()
    )
