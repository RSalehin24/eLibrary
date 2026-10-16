import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.access.publication_models import PreparedPublication
from apps.accounts.models import User
from apps.catalog.editorial.service import publish_book, review_book_editorial
from apps.catalog.models import UserBook
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from django.test import Client
from source_processing_fixtures import execute_source_job

pytestmark = pytest.mark.django_db


def test_a_curated_reviewed_source_book_can_be_read_without_an_extra_preparation_request(
    curated_job,
):
    execute_source_job(curated_job)
    assert curated_job.state == "succeeded"
    book = review_book_editorial(
        curated_job.requested_by, curated_job.book_id, curated_job.book.updated_at
    )
    book = publish_book(curated_job.requested_by, book.pk, book.updated_at)
    reader = User.objects.create_user(email="curated-book-reader@library.test")
    PermissionGrant.objects.create(
        user=reader, book=book, scope=PermissionScope.READ_DURABLE
    )
    client = Client()
    client.force_login(reader)
    response = client.post(f"/api/v1/reading/books/{book.slug}/launch/")
    assert response.status_code == 200
    session = response.json()
    chapter = next(
        chapter
        for chapter in session["chapters"]
        if chapter["label"] == "নতুন উৎসের বই" or "অধ্যায়" in chapter["label"]
    )
    content = client.get(session["resource_base"] + chapter["path"])
    assert content.status_code == 200
    assert "বইয়ের মূল বাংলা লেখা" in b"".join(content.streaming_content).decode()
    assert not UserBook.objects.exists()


def test_failed_resource_preparation_resumes_without_replacing_completed_exports(
    curated_job, monkeypatch
):
    from apps.processing.jobs.preparation import prepare_checked_asset

    def unavailable(_asset):
        raise ExecutionFailure(FailureKind.TRANSIENT, "storage_unavailable")

    curated_job.max_attempts = 1
    curated_job.save()
    monkeypatch.setattr(
        "apps.ingestion.source_processing.reading_preparation.prepare_checked_asset",
        unavailable,
    )
    execute_source_job(curated_job)
    assert curated_job.state == "failed" and curated_job.checkpoint["assets_published"]
    path, revision = curated_job.asset.file.name, curated_job.asset.updated_at
    resolve_source_job(
        curated_job.requested_by,
        curated_job.pk,
        {"choice": "resume_preparation", "expected_updated_at": curated_job.updated_at},
    )
    monkeypatch.setattr(
        "apps.ingestion.source_processing.reading_preparation.prepare_checked_asset",
        prepare_checked_asset,
    )
    curated_job.refresh_from_db()
    execute_source_job(curated_job)
    assert curated_job.state == "succeeded" and curated_job.asset.file.name == path
    assert curated_job.asset.updated_at == revision
    assert (
        PreparedPublication.objects.get(checksum=curated_job.asset.checksum).state
        == "ready"
    )
