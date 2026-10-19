import hashlib
import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.catalog.models import Book, GeneratedAsset, MetadataVersion
from apps.ingestion.source_processing.issues import available_source_choices
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from apps.processing.jobs.preparation import prepare_checked_asset
from django.core.files.base import ContentFile
from django.db import connections
from PIL import Image
from regeneration_fixtures import request_regeneration
from rest_framework.test import APIClient
from source_processing_fixtures import curated_source, execute_source_job

pytestmark = pytest.mark.django_db


def test_preparation_recovery_does_not_repeat_content_or_asset_replacement(
    regeneration, tmp_path, monkeypatch
):
    actor, book, _, _, publication = regeneration
    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.curate_source_job",
        lambda ownership, current: (curated_source(tmp_path), current.checkpoint),
    )

    def unavailable(_asset):
        raise ExecutionFailure(FailureKind.PERMANENT, "storage_unavailable")

    monkeypatch.setattr(
        "apps.ingestion.source_processing.reading_preparation.prepare_checked_asset",
        unavailable,
    )
    job = request_regeneration(regeneration)
    execute_source_job(job)
    assert job.state == "failed" and not job.checkpoint.get("content_committed")
    assert not job.checkpoint.get("assets_published")
    book.refresh_from_db()
    assert (
        book.main_content_html == "<p>Previous text</p>" and book.state == "published"
    )
    assert available_source_choices(job) == ["resume_preparation", "cancel"]
    staged = job.checkpoint["staged_assets"]["epub"]
    path, checksum = staged["file"], staged["checksum"]
    resolve_source_job(
        actor,
        job.pk,
        {"choice": "resume_preparation", "expected_updated_at": job.updated_at},
    )
    monkeypatch.setattr(
        "apps.ingestion.source_processing.reading_preparation.prepare_checked_asset",
        prepare_checked_asset,
    )
    job.refresh_from_db()
    execute_source_job(job)
    assert job.state == "succeeded" and job.asset.file.name == path
    assert job.asset.checksum == checksum
    publication.refresh_from_db()
    assert publication.state == "ready"
    assert MetadataVersion.objects.filter(book=book, source="regeneration").count() == 1


def test_existing_cover_is_reused_in_regenerated_files_if_the_source_has_no_cover(
    regeneration, tmp_path, monkeypatch
):
    _, book, _, _, _ = regeneration
    image = io.BytesIO()
    Image.new("RGB", (24, 40), "blue").save(image, "PNG")
    previous = image.getvalue()
    cover = GeneratedAsset.objects.create(
        book=book, asset_type="cover", status="ready", content_type="image/png"
    )
    cover.file.save("previous.png", ContentFile(previous))
    old_name = cover.file.name
    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.curate_source_job",
        lambda ownership, current: (curated_source(tmp_path), current.checkpoint),
    )
    job = request_regeneration(regeneration)
    execute_source_job(job)
    assert job.state == "succeeded", job.error_code
    cover.refresh_from_db()
    assert cover.checksum == hashlib.sha256(previous).hexdigest()
    assert cover.file.storage.exists(old_name)
    epub = GeneratedAsset.objects.get(book=book, asset_type="epub")
    with epub.file.open("rb") as handle, zipfile.ZipFile(handle) as archive:
        assert any(
            archive.read(name) == previous
            for name in archive.namelist()
            if name.endswith(".png")
        )


def test_metadata_authority_revocation_stops_regeneration_before_fetching(
    regeneration, monkeypatch
):
    actor, _, _, _, _ = regeneration
    job = request_regeneration(regeneration)
    actor.is_staff = False
    actor.save()
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.PROCESSING_MANAGE)

    def unexpected_fetch(*arguments):
        pytest.fail("A revoked metadata editor must not fetch source content.")

    monkeypatch.setattr(
        "apps.ingestion.source_processing.worker.curate_source_job", unexpected_fetch
    )
    execute_source_job(job)
    assert job.state == "failed" and job.error_code == "permission_revoked"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_operation", [True, False])
def test_concurrent_regeneration_commands_create_only_one_operation(
    regeneration, same_operation
):
    actor, book, _, _, _ = regeneration
    barrier = Barrier(2)
    identifier = str(uuid4())

    def submit(index):
        try:
            client = APIClient()
            client.force_authenticate(actor)
            barrier.wait(timeout=5)
            return client.post(
                f"/api/v1/manage/books/{book.slug}/regenerate/",
                {
                    "operation_id": identifier if same_operation else str(uuid4()),
                    "expected_updated_at": book.updated_at.isoformat(),
                },
                format="json",
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(submit, range(2)))
    assert statuses == ([202, 202] if same_operation else [202, 409])
    assert BackgroundJob.objects.filter(input__regenerate_book=True).count() == 1
    assert MetadataVersion.objects.filter(book=book, source="editorial").count() == 1


@pytest.mark.django_db(transaction=True)
def test_removal_and_regeneration_cannot_leave_a_deleted_book_with_new_work(
    regeneration,
):
    actor, book, _, _, _ = regeneration
    barrier = Barrier(2)
    path = f"/api/v1/manage/books/{book.slug}/"
    values = {"expected_updated_at": book.updated_at.isoformat()}

    def submit(action):
        try:
            client = APIClient()
            client.force_authenticate(actor)
            barrier.wait(timeout=5)
            if action == "remove":
                return client.delete(path, values, format="json").status_code
            return client.post(
                path + "regenerate/",
                {**values, "operation_id": str(uuid4())},
                format="json",
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        removed, regenerated = list(pool.map(submit, ["remove", "regenerate"]))
    book = Book.objects.get(pk=book.pk)
    assert (removed, regenerated) in {(204, 404), (204, 409), (409, 202)}
    assert not (
        book.deleted_at
        and BackgroundJob.objects.filter(
            book=book, input__regenerate_book=True
        ).exists()
    )
