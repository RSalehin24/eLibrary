from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.processing.job_models import BackgroundJob
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PATH = "/api/v1/manage/jobs/"


def manager_client(job):
    client = APIClient()
    client.force_authenticate(job.requested_by)
    return client


def bulk_values(job, **changes):
    return {
        "operation_id": str(uuid4()),
        "action": "pause",
        "entries": [
            {"id": str(job.pk), "expected_updated_at": job.updated_at.isoformat()}
        ],
        **changes,
    }


def copy_preparation(job, **changes):
    return BackgroundJob.objects.create(
        requested_by=job.requested_by,
        kind="prepare_epub",
        book=job.book,
        asset=job.asset,
        available_at=timezone.now(),
        **changes,
    )


def test_queue_views_partition_active_history_and_recovery(preparation_job):
    client = manager_client(preparation_job)
    for state in (
        "running",
        "retry_wait",
        "paused",
        "succeeded",
        "failed",
        "cancelled",
        "needs_attention",
    ):
        copy_preparation(preparation_job, state=state)
    expected = {
        "active": {"queued", "running", "retry_wait", "paused"},
        "history": {"succeeded", "failed", "cancelled"},
        "recovery": {"retry_wait", "paused", "failed", "needs_attention"},
    }
    for view, states in expected.items():
        response = client.get(PATH, {"view": view})
        assert response.status_code == 200
        assert {entry["state"] for entry in response.json()["entries"]} == states
    assert not client.get(PATH, {"view": "active", "state": "succeeded"}).json()[
        "entries"
    ]


def test_queue_search_uses_book_title_error_or_job_id_without_private_inputs(
    preparation_job,
):
    client = manager_client(preparation_job)
    preparation_job.error_code = "source_connection_unavailable"
    preparation_job.input = {"secret": "DO_NOT_SEARCH_PRIVATE_INPUT"}
    preparation_job.save()
    for query in (
        preparation_job.book.title,
        "connection_unavailable",
        str(preparation_job.pk),
    ):
        response = client.get(PATH, {"q": query})
        assert response.status_code == 200
        assert response.json()["entries"][0]["id"] == str(preparation_job.pk)
    assert not client.get(PATH, {"q": "DO_NOT_SEARCH_PRIVATE_INPUT"}).json()["entries"]
    assert (
        client.get(PATH, {"error_code": preparation_job.error_code}).json()[
            "pagination"
        ]["total_count"]
        == 1
    )
    assert not client.get(PATH, {"error_code": "other_failure"}).json()["entries"]


def test_source_coverage_filter_uses_persisted_verification_and_safe_summary(
    source_job,
):
    client = manager_client(source_job)
    source_job.requested_by.is_staff = True
    source_job.requested_by.save()
    path = PATH + str(source_job.pk) + "/"
    verification = {
        "verified": True,
        "source_pages": 3,
        "fetched_pages": 3,
        "expected_chapters": 2,
        "collected_chapters": 2,
        "issues": [],
    }
    source_job.checkpoint = {
        "source_summary": {"verification": verification},
        "exports_verified": True,
        "private": "PRIVATE PATH",
    }
    source_job.save()
    response = client.get(PATH, {"coverage": "verified"})
    assert response.status_code == 200 and len(response.json()["entries"]) == 1
    assert response.json()["entries"][0]["verification"]["collected_chapters"] == 2
    assert response.json()["entries"][0]["exports_verified"] is True
    assert "PRIVATE PATH" not in response.content.decode()
    assert not client.get(PATH, {"coverage": "incomplete"}).json()["entries"]
    source_job.checkpoint["source_summary"]["verification"]["verified"] = False
    source_job.save()
    assert len(client.get(PATH, {"coverage": "incomplete"}).json()["entries"]) == 1
    source_job.checkpoint = {}
    source_job.save()
    assert len(client.get(PATH, {"coverage": "unverified"}).json()["entries"]) == 1
    assert client.get(path).json()["verification"] is None


@pytest.mark.parametrize(
    "parameters",
    [
        {"view": "unknown"},
        {"coverage": "unknown"},
        {"error_code": "path/to/private"},
        {"q": "x" * 121},
    ],
)
def test_invalid_queue_filter_values_fail_validation(preparation_job, parameters):
    assert manager_client(preparation_job).get(PATH, parameters).status_code == 400


def test_bulk_control_is_revision_pinned_idempotent_and_preserves_history(
    preparation_job,
):
    client = manager_client(preparation_job)
    values = bulk_values(preparation_job)
    first = client.post(PATH + "bulk-control/", values, format="json")
    assert first.status_code == 200
    assert first.json()["entries"] == [
        {"id": str(preparation_job.pk), "outcome": "accepted", "code": ""}
    ]
    preparation_job.refresh_from_db()
    assert preparation_job.state == "paused" and preparation_job.dispatches.count() == 1
    revision = preparation_job.updated_at
    assert (
        client.post(PATH + "bulk-control/", values, format="json").json()
        == first.json()
    )
    preparation_job.refresh_from_db()
    assert preparation_job.updated_at == revision
    assert AuditLog.objects.filter(pk=values["operation_id"]).count() == 1
    resume = bulk_values(preparation_job, action="resume")
    assert client.post(PATH + "bulk-control/", resume, format="json").status_code == 200
    preparation_job.refresh_from_db()
    assert preparation_job.state == "queued" and preparation_job.dispatches.count() == 2


def test_bulk_control_reports_each_conflict_and_missing_job_without_losing_valid_items(
    preparation_job,
):
    client = manager_client(preparation_job)
    stale = copy_preparation(preparation_job)
    stale_revision = stale.updated_at.isoformat()
    stale.save()
    values = bulk_values(preparation_job)
    values["entries"] += [
        {"id": str(stale.pk), "expected_updated_at": stale_revision},
        {"id": str(uuid4()), "expected_updated_at": stale_revision},
    ]
    result = client.post(PATH + "bulk-control/", values, format="json")
    assert result.status_code == 200
    assert [entry["outcome"] for entry in result.json()["entries"]] == [
        "accepted",
        "conflict",
        "not_found",
    ]
    stale.refresh_from_db()
    assert stale.state == "queued"


def test_bulk_receipt_cannot_be_reused_by_other_actor_or_action(preparation_job):
    client = manager_client(preparation_job)
    values = bulk_values(preparation_job)
    assert client.post(PATH + "bulk-control/", values, format="json").status_code == 200
    assert (
        client.post(
            PATH + "bulk-control/", {**values, "action": "cancel"}, format="json"
        ).status_code
        == 409
    )
    other = User.objects.create_user(
        email="bulk-control-other@library.test", is_staff=True
    )
    client.force_authenticate(other)
    assert client.post(PATH + "bulk-control/", values, format="json").status_code == 409


@pytest.mark.parametrize(
    "case", ["empty", "duplicate", "over_limit", "extra_entry_field", "unknown_action"]
)
def test_bulk_input_validation_is_bounded_and_atomic(preparation_job, case):
    client = manager_client(preparation_job)
    values = bulk_values(preparation_job)
    if case == "empty":
        values["entries"] = []
    if case == "duplicate":
        values["entries"] *= 2
    if case == "over_limit":
        values["entries"] *= 101
    if case == "extra_entry_field":
        values["entries"][0]["state"] = "paused"
    if case == "unknown_action":
        values["action"] = "delete"
    assert client.post(PATH + "bulk-control/", values, format="json").status_code == 400
    preparation_job.refresh_from_db()
    assert preparation_job.state == "queued"
    assert not AuditLog.objects.filter(pk=values["operation_id"]).exists()


def test_bulk_controls_require_global_authority_and_csrf(preparation_job):
    values = bulk_values(preparation_job)
    actor = preparation_job.requested_by
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(actor)
    assert client.post(PATH + "bulk-control/", values, format="json").status_code == 403
    csrf = client.get("/api/v1/auth/session/").data["csrf_token"]
    assert (
        client.post(
            PATH + "bulk-control/", values, format="json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 200
    )
    actor.is_staff = False
    actor.save()
    assert (
        client.post(
            PATH + "bulk-control/", values, format="json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 403
    )
