from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.access.publication_models import PreparedPublication
from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.attempts import claim_attempt
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PATH = "/api/v1/manage/jobs/bulk-control/"


def client_for(job):
    client = APIClient()
    client.force_authenticate(job.requested_by)
    return client


def command(job, action, **changes):
    entry = {"id": str(job.pk), "expected_updated_at": job.updated_at.isoformat()}
    if job.book_id:
        entry["expected_book_updated_at"] = job.book.updated_at.isoformat()
    return {
        "operation_id": str(uuid4()),
        "action": action,
        "entries": [entry],
        **changes,
    }


def fail_source(job):
    ownership = claim_attempt(job.dispatches.get(generation=job.generation).pk)
    fail_attempt(
        ownership, AttemptFailure(FailureKind.PERMANENT, "source_checkpoint_invalid")
    )
    job.refresh_from_db()


def test_bulk_source_retry_is_revision_pinned_idempotent_and_source_only(
    source_job, preparation_job
):
    fail_source(source_job)
    values = command(source_job, "retry_source")
    values["entries"].append(
        {
            "id": str(preparation_job.pk),
            "expected_updated_at": preparation_job.updated_at.isoformat(),
        }
    )
    response = client_for(source_job).post(PATH, values, format="json")
    assert response.status_code == 200
    assert [entry["outcome"] for entry in response.json()["entries"]] == [
        "accepted",
        "not_found",
    ]
    source_job.refresh_from_db()
    assert source_job.state == "queued" and source_job.attempts.count() == 1
    assert source_job.dispatches.count() == 2
    assert (
        client_for(source_job).post(PATH, values, format="json").json()
        == response.json()
    )
    assert source_job.dispatches.count() == 2


def test_bulk_source_retry_reports_stale_and_missing_items(source_job):
    fail_source(source_job)
    values = command(source_job, "retry_source")
    source_job.save()
    values["entries"].append(
        {"id": str(uuid4()), "expected_updated_at": source_job.updated_at.isoformat()}
    )
    response = client_for(source_job).post(PATH, values, format="json")
    assert [entry["outcome"] for entry in response.json()["entries"]] == [
        "conflict",
        "not_found",
    ]
    assert source_job.dispatches.count() == 1


def test_bulk_recreate_reuses_book_and_receipt_replays_after_revision_changes(
    regeneration,
):
    from regeneration_fixtures import request_regeneration

    _, book, _, _, _ = regeneration
    job = request_regeneration(regeneration)
    fail_source(job)
    job.book.refresh_from_db()
    values = command(job, "recreate_source")
    client = client_for(job)
    response = client.post(PATH, values, format="json")
    assert (
        response.status_code == 200
        and response.json()["entries"][0]["outcome"] == "accepted"
    )
    job.refresh_from_db()
    assert job.state == "cancelled"
    assert book.background_jobs.count() == 2
    assert client.post(PATH, values, format="json").json() == response.json()
    assert book.background_jobs.count() == 2
    assert AuditLog.objects.filter(verb="processing.jobs.bulk_control").count() == 1


def test_bulk_archive_preserves_files_personal_data_and_history(regeneration):
    from regeneration_fixtures import request_regeneration

    _, book, _, asset, publication = regeneration
    job = request_regeneration(regeneration)
    fail_source(job)
    job.book.refresh_from_db()
    previous = (asset.legacy_path, publication.pk)
    response = client_for(job).post(PATH, command(job, "archive_book"), format="json")
    assert (
        response.status_code == 200
        and response.json()["entries"][0]["outcome"] == "accepted"
    )
    job.refresh_from_db()
    book.refresh_from_db()
    asset.refresh_from_db()
    assert (
        job.state == "cancelled"
        and book.state == "archived"
        and book.deleted_at is None
    )
    assert (
        asset.legacy_path == previous[0]
        and PreparedPublication.objects.filter(pk=previous[1]).exists()
    )
    assert job.attempts.count() == 1


@pytest.mark.parametrize("action", ["recreate_source", "archive_book"])
def test_bulk_book_actions_require_pinned_book_revision(regeneration, action):
    from regeneration_fixtures import request_regeneration

    job = request_regeneration(regeneration)
    fail_source(job)
    job.book.refresh_from_db()
    values = command(job, action)
    values["entries"][0].pop("expected_book_updated_at")
    assert client_for(job).post(PATH, values, format="json").status_code == 400
    assert not AuditLog.objects.filter(verb="processing.jobs.bulk_control").exists()


def test_bulk_archive_book_revision_conflict_never_cancels_existing_job(regeneration):
    from regeneration_fixtures import request_regeneration

    job = request_regeneration(regeneration)
    fail_source(job)
    job.book.refresh_from_db()
    values = command(job, "archive_book")
    job.book.save()
    response = client_for(job).post(PATH, values, format="json")
    assert (
        response.status_code == 200
        and response.json()["entries"][0]["outcome"] == "conflict"
    )
    job.refresh_from_db()
    assert job.state == "failed"


@pytest.mark.parametrize("action", ["archive_book", "recreate_source"])
def test_processing_only_manager_cannot_change_book_or_cancel_recovery(
    regeneration, action
):
    from regeneration_fixtures import request_regeneration

    job = request_regeneration(regeneration)
    fail_source(job)
    job.book.refresh_from_db()
    actor = User.objects.create_user(email="source-bulk-processing-only@example.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.PROCESSING_MANAGE)
    client = APIClient()
    client.force_authenticate(actor)
    response = client.post(PATH, command(job, action), format="json")
    assert (
        response.status_code == 200
        and response.json()["entries"][0]["outcome"] == "not_found"
    )
    job.refresh_from_db()
    assert job.state == "failed"


def test_bulk_retry_and_recreate_cannot_bypass_unchanged_code_defect(regeneration):
    from regeneration_fixtures import request_regeneration

    job = request_regeneration(regeneration)
    ownership = claim_attempt(job.dispatches.get(generation=job.generation).pk)
    fail_attempt(
        ownership,
        AttemptFailure(FailureKind.PERMANENT, "source_export_content_mismatch"),
    )
    job.refresh_from_db()
    job.book.refresh_from_db()
    client = client_for(job)
    for action in ("retry_source", "recreate_source"):
        response = client.post(PATH, command(job, action), format="json")
        assert (
            response.status_code == 200
            and response.json()["entries"][0]["outcome"] == "conflict"
        )
    job.refresh_from_db()
    assert job.state == "failed" and job.book.background_jobs.count() == 1
    detail = client.get(f"/api/v1/manage/jobs/{job.pk}/").json()
    assert detail["source_recovery_actions"] == ["archive_book"]


def test_bulk_receipt_pins_book_revision_and_single_job_controls_remain_distinct(
    regeneration,
):
    from regeneration_fixtures import request_regeneration

    job = request_regeneration(regeneration)
    fail_source(job)
    job.book.refresh_from_db()
    values = command(job, "archive_book")
    client = client_for(job)
    assert client.post(PATH, values, format="json").status_code == 200
    job.book.refresh_from_db()
    values["entries"][0]["expected_book_updated_at"] = job.book.updated_at.isoformat()
    assert client.post(PATH, values, format="json").status_code == 409
    assert (
        client.post(
            f"/api/v1/manage/jobs/{job.pk}/",
            {
                "action": "retry_source",
                "expected_updated_at": job.updated_at.isoformat(),
            },
            format="json",
        ).status_code
        == 400
    )


def test_source_recovery_actions_use_bounded_queries_and_omit_private_inputs(
    regeneration,
):
    from regeneration_fixtures import request_regeneration

    job = request_regeneration(regeneration)
    fail_source(job)
    job.book.refresh_from_db()
    client = client_for(job)
    path = f"/api/v1/manage/jobs/?kind=process_source&book={job.book_id}"
    with CaptureQueriesContext(connection) as single:
        first = client.get(path)
    for _ in range(5):
        BackgroundJob.objects.create(
            requested_by=job.requested_by,
            book=job.book,
            source_record=job.source_record,
            kind="process_source",
            state="failed",
            input={**job.input, "private": "SOURCE_BULK_SECRET"},
            checkpoint=job.checkpoint,
            error_code=job.error_code,
            available_at=job.available_at,
        )
    with CaptureQueriesContext(connection) as many:
        response = client.get(path)
    assert first.status_code == response.status_code == 200
    assert len(response.json()["entries"]) == 6
    assert len(single) == len(many)
    assert "SOURCE_BULK_SECRET" not in response.content.decode()
    assert all(
        "recreate_source" in entry["source_recovery_actions"]
        for entry in response.json()["entries"]
    )
    assert all(entry["book"]["updated_at"] for entry in response.json()["entries"])
