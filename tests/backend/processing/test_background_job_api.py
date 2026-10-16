from contextlib import nullcontext
from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import GeneratedAsset, UserBook
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.attempts import checkpoint_attempt, claim_attempt
from apps.processing.jobs.worker import run_background_job
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def manager_client(job):
    client = APIClient()
    client.force_authenticate(job.requested_by)
    return client


def preparation_fields(asset):
    return {
        "operation_id": str(uuid4()),
        "expected_updated_at": asset.updated_at.isoformat(),
    }


def test_prepare_command_persists_an_outbox_and_returns_an_operation_status(
    preparation_job,
):
    client = manager_client(preparation_job)
    asset = preparation_job.asset
    fields = preparation_fields(asset)
    response = client.post(
        f"/api/v1/manage/assets/{asset.pk}/prepare/", fields, format="json"
    )
    assert response.status_code == 202
    job = BackgroundJob.objects.get(pk=response.data["operation_id"])
    assert job.dispatches.count() == 1 and job.input == {
        "asset_revision": asset.updated_at.isoformat()
    }
    assert response.data["status_url"] == f"/api/v1/manage/jobs/{job.pk}/"
    duplicate = client.post(
        f"/api/v1/manage/assets/{asset.pk}/prepare/", fields, format="json"
    )
    assert duplicate.status_code == 202 and duplicate.data == response.data
    assert BackgroundJob.objects.count() == 2
    run_background_job(job.dispatches.get().pk, lambda _: nullcontext())
    detail = client.get(response.data["status_url"])
    assert detail.data["state"] == "succeeded" and detail.data["checkpoint_saved"]
    assert detail.data["stage"] == "prepared" and len(detail.data["attempts"]) == 1


@pytest.mark.parametrize(
    "permission", ["anonymous", "owner", "scoped_processing", "metadata"]
)
def test_job_endpoints_reject_reader_and_non_global_processing_access(
    preparation_job, permission
):
    client = APIClient()
    if permission != "anonymous":
        user = User.objects.create_user(email=f"{permission}@library.test")
        client.force_authenticate(user)
        if permission == "owner":
            UserBook.objects.create(user=user, book=preparation_job.book)
        else:
            PermissionGrant.objects.create(
                user=user,
                book=preparation_job.book,
                scope=PermissionScope.METADATA_EDIT
                if permission == "metadata"
                else PermissionScope.PROCESSING_MANAGE,
            )
    assert client.get("/api/v1/manage/jobs/").status_code == 403
    assert client.get(f"/api/v1/manage/jobs/{preparation_job.pk}/").status_code == 403
    assert (
        client.get(
            f"/api/v1/manage/books/{preparation_job.book.slug}/assets/"
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/manage/assets/{preparation_job.asset_id}/prepare/",
            preparation_fields(preparation_job.asset),
            format="json",
        ).status_code
        == 403
    )


def test_global_processing_grant_enables_job_access_without_staff(preparation_job):
    user = User.objects.create_user(email="global-processor@library.test")
    PermissionGrant.objects.create(user=user, scope=PermissionScope.PROCESSING_MANAGE)
    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/v1/manage/jobs/")
    assert (
        response.status_code == 200
        and response.data["entries"][0]["can_edit_book"] is False
    )
    assert (
        client.post(
            f"/api/v1/manage/assets/{preparation_job.asset_id}/prepare/",
            preparation_fields(preparation_job.asset),
            format="json",
        ).status_code
        == 202
    )


def test_job_representations_omit_private_inputs_checkpoints_and_storage_paths(
    preparation_job,
):
    preparation_job.input["private_value"] = "synthetic-private-input"
    preparation_job.checkpoint = {"private_value": "synthetic-private-checkpoint"}
    preparation_job.save()
    client = manager_client(preparation_job)
    detail = client.get(f"/api/v1/manage/jobs/{preparation_job.pk}/")
    assets = client.get(f"/api/v1/manage/books/{preparation_job.book.slug}/assets/")
    encoded = detail.content + assets.content
    assert detail.status_code == assets.status_code == 200
    assert (
        b"synthetic-private" not in encoded
        and preparation_job.asset.legacy_path.encode() not in encoded
    )
    assert detail["Cache-Control"] == "private, no-store"
    assert detail["X-Robots-Tag"] == "noindex"


def test_job_list_filters_paginate_and_keep_query_counts_bounded(preparation_job):
    client = manager_client(preparation_job)
    BackgroundJob.objects.bulk_create(
        [
            BackgroundJob(
                requested_by=preparation_job.requested_by,
                book=preparation_job.book,
                asset=preparation_job.asset,
                kind="prepare_epub",
                available_at=timezone.now(),
            )
            for _ in range(100)
        ]
    )
    with CaptureQueriesContext(connection) as small:
        assert len(client.get("/api/v1/manage/jobs/?limit=1").data["entries"]) == 1
    with CaptureQueriesContext(connection) as large:
        response = client.get("/api/v1/manage/jobs/?limit=100")
    assert len(response.data["entries"]) == 100 and len(large) == len(small) <= 3
    assert response.data["pagination"] == {"page": 1, "limit": 100, "total_count": 101}
    assert len(client.get("/api/v1/manage/jobs/").data["entries"]) == 50
    assert client.get("/api/v1/manage/jobs/?state=succeeded").data["entries"] == []
    assert client.get("/api/v1/manage/jobs/?state=unknown").status_code == 400
    assert client.get("/api/v1/manage/jobs/?limit=101").status_code == 400


def test_preparation_rejects_missing_revision_stale_asset_and_unavailable_asset(
    preparation_job,
):
    client = manager_client(preparation_job)
    path = f"/api/v1/manage/assets/{preparation_job.asset_id}/prepare/"
    assert (
        client.post(path, {"operation_id": str(uuid4())}, format="json").status_code
        == 400
    )
    fields = preparation_fields(preparation_job.asset)
    preparation_job.asset.save()
    assert client.post(path, fields, format="json").status_code == 409
    preparation_job.asset.status = "failed"
    preparation_job.asset.save()
    assert (
        client.post(
            path, preparation_fields(preparation_job.asset), format="json"
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/manage/assets/{uuid4()}/prepare/", fields, format="json"
        ).status_code
        == 404
    )


def test_operation_identifier_cannot_be_reused_for_another_asset(preparation_job):
    client = manager_client(preparation_job)
    other = GeneratedAsset.objects.create(
        book=preparation_job.book, asset_type="html", status="ready"
    )
    fields = {**preparation_fields(other), "operation_id": str(preparation_job.pk)}
    response = client.post(
        f"/api/v1/manage/assets/{other.pk}/prepare/", fields, format="json"
    )
    assert response.status_code == 409 and BackgroundJob.objects.count() == 1


def test_running_pause_stays_requested_until_a_checkpoint_and_revisions_prevent_replay(
    preparation_job,
):
    client = manager_client(preparation_job)
    ownership = claim_attempt(preparation_job.dispatches.get().pk)
    preparation_job.refresh_from_db()
    path = f"/api/v1/manage/jobs/{preparation_job.pk}/"
    fields = {
        "action": "pause",
        "expected_updated_at": preparation_job.updated_at.isoformat(),
    }
    assert client.post(path, fields, format="json").status_code == 202
    pending = client.get(path)
    assert (
        pending.data["state"] == "running"
        and pending.data["requested_action"] == "pause"
    )
    assert pending.data["actions"] == ["cancel"]
    assert client.post(path, fields, format="json").status_code == 409
    assert not checkpoint_attempt(ownership, {"unit": 1}, "prepared")
    paused = client.get(path)
    assert paused.data["state"] == "paused" and paused.data["actions"] == [
        "resume",
        "cancel",
    ]
    assert (
        client.post(
            path,
            {"action": "resume", "expected_updated_at": paused.data["updated_at"]},
            format="json",
        ).status_code
        == 202
    )
    assert client.get(path).data["state"] == "queued"


def test_real_session_requires_csrf_for_background_commands(preparation_job):
    actor = preparation_job.requested_by
    actor.totp_required = False
    actor.save()
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(actor)
    path = f"/api/v1/manage/assets/{preparation_job.asset_id}/prepare/"
    fields = preparation_fields(preparation_job.asset)
    assert client.post(path, fields, format="json").status_code == 403
    csrf = client.get("/api/v1/auth/session/").data["csrf_token"]
    assert (
        client.post(path, fields, format="json", HTTP_X_CSRFTOKEN=csrf).status_code
        == 202
    )
