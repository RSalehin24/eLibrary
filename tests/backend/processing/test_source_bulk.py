from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import BackgroundJob

pytestmark = pytest.mark.django_db


def selection(entry):
    return {
        "source_id": str(entry.pk),
        "operation_id": str(uuid4()),
        "expected_updated_at": entry.updated_at.isoformat(),
    }


def test_rejected_bulk_records_return_whole_validation_messages(source_job, client):
    client.force_login(source_job.requested_by)
    entry = SourceCatalogEntry.objects.create(
        source_url="https://outside.test/books/book/", title="অন্য উৎস"
    )
    response = client.post(
        "/api/v1/manage/sources/process-selection/",
        {"entries": [selection(entry)]},
        content_type="application/json",
    )
    assert response.status_code == 200
    errors = response.json()["entries"][0]["error"]["field_errors"]
    assert (
        len(errors["source"]) == 1
        and "Configure an allowed canonical" in errors["source"][0]
    )
    assert BackgroundJob.objects.count() == 1


def test_bulk_commands_preserve_per_record_results_and_idempotent_requests(
    source_job, client
):
    client.force_login(source_job.requested_by)
    fresh = SourceCatalogEntry.objects.create(
        source_url="https://source.test/books/bulk/", title="নির্বাচিত উৎস"
    )
    accepted, stale, missing = (
        selection(fresh),
        selection(source_job.source_record),
        selection(fresh),
    )
    missing["source_id"] = str(uuid4())
    response = client.post(
        "/api/v1/manage/sources/process-selection/",
        {"entries": [accepted, stale, missing]},
        content_type="application/json",
    )
    assert response.status_code == 200
    results = response.json()["entries"]
    assert [result["accepted"] for result in results] == [True, False, False]
    assert [result["error"]["code"] for result in results[1:]] == [
        "state_conflict",
        "not_found",
    ]
    assert BackgroundJob.objects.count() == 2
    again = client.post(
        "/api/v1/manage/sources/process-selection/",
        {"entries": [accepted]},
        content_type="application/json",
    )
    assert again.json()["entries"] == results[:1] and BackgroundJob.objects.count() == 2
    assert (
        response["Cache-Control"] == "private, no-store"
        and response["X-Robots-Tag"] == "noindex"
    )


@pytest.mark.parametrize(
    "failure",
    [
        "empty",
        "duplicate_source",
        "duplicate_operation",
        "too_many",
        "unknown_field",
        "invalid_identifier",
    ],
)
def test_invalid_bulk_selections_are_rejected_before_any_write(
    source_job, client, failure
):
    client.force_login(source_job.requested_by)
    values = selection(source_job.source_record)
    entries = [values]
    if failure == "empty":
        entries = []
    elif failure == "duplicate_source":
        entries.append({**values, "operation_id": str(uuid4())})
    elif failure == "duplicate_operation":
        entries.append({**values, "source_id": str(uuid4())})
    elif failure == "too_many":
        entries = [
            {**values, "source_id": str(uuid4()), "operation_id": str(uuid4())}
            for _ in range(101)
        ]
    elif failure == "unknown_field":
        values["raw_data"] = "must not write"
    else:
        values["source_id"] = "invalid"
    response = client.post(
        "/api/v1/manage/sources/process-selection/",
        {"entries": entries},
        content_type="application/json",
    )
    assert response.status_code == 400 and BackgroundJob.objects.count() == 1


def test_bulk_commands_require_processing_authority_and_csrf(source_job):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    client.force_login(source_job.requested_by)
    path = "/api/v1/manage/sources/process-selection/"
    assert (
        client.post(
            path,
            {"entries": [selection(source_job.source_record)]},
            content_type="application/json",
        ).status_code
        == 403
    )
    reader = User.objects.create_user(email="bulk-reader@library.test")
    client.force_login(reader)
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    assert (
        client.post(
            path,
            {"entries": [selection(source_job.source_record)]},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 403
    )
