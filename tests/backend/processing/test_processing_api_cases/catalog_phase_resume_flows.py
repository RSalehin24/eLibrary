import pytest
from apps.processing.models import BookCreationRequest, BookRecord
from apps.processing.services import get_sync_state

from tests.backend.processing.test_processing_api_cases.helpers import (
    advance_processing_sync,
    login_processing_admin,
    post_processing_mutation,
    record_payload,
)


@pytest.mark.django_db
def test_manual_sync_start_takes_over_paused_automation_runtime(client):
    login_processing_admin(client)
    sync_state = get_sync_state()
    sync_state.remote_pages = [
        [record_payload("shared-page-1", name="Shared Page One")],
        [record_payload("shared-page-2", name="Shared Page Two")],
        [],
    ]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["runMode"] == "catalog_automation"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/pause/",
    )
    assert payload["sync"]["status"] == "pausing"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "paused"
    assert payload["sync"]["runMode"] == "catalog_automation"
    assert payload["sync"]["fetchedCount"] == 1

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "manual"
    assert (
        payload["sync"]["message"] == "Continuing catalog sync from the saved endpoint."
    )
    assert payload["sync"]["fetchedCount"] == 1
    assert payload["sync"]["pageIndex"] == 1
    assert payload["sync"]["progress"]["savedData"]["fetchedCount"] == 1
    assert payload["sync"]["progress"]["savedData"]["nextPageIndex"] == 1
    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "idle"
    assert BookRecord.objects.filter(pk="shared-page-2").exists()
    assert not BookCreationRequest.objects.exists()


@pytest.mark.django_db
def test_catalog_automation_run_takes_over_paused_manual_runtime(client):
    login_processing_admin(client)

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [record_payload("resume-auto-page-1", name="Resume Auto Page One")],
                [record_payload("resume-auto-page-2", name="Resume Auto Page Two")],
                [],
            ]
        },
    )
    assert payload["sync"]["runMode"] == "manual"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/pause/",
    )
    assert payload["sync"]["status"] == "pausing"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "paused"
    assert payload["sync"]["runMode"] == "manual"
    assert payload["sync"]["fetchedCount"] == 1

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "catalog_automation"
    assert (
        payload["sync"]["message"]
        == "Continuing automated catalog sync from the saved endpoint."
    )
    assert payload["sync"]["fetchedCount"] == 1
    assert payload["sync"]["pageIndex"] == 1
    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "idle"
    assert BookCreationRequest.objects.exists()


@pytest.mark.django_db
def test_catalog_automation_request_creation_phase_can_pause_and_resume(
    client, monkeypatch
):
    login_processing_admin(client)
    monkeypatch.setattr(
        "apps.processing.service_modules.service_imports_and_constants.CATALOG_REQUEST_CREATION_BATCH_SIZE",
        1,
    )
    BookRecord.objects.create(
        id="phase-request-a",
        name="Phase Request A",
        url="https://example.test/books/phase-request-a",
        category="Reference",
        writer="Writer One",
        publisher="Press",
    )
    BookRecord.objects.create(
        id="phase-request-b",
        name="Phase Request B",
        url="https://example.test/books/phase-request-b",
        category="Reference",
        writer="Writer Two",
        publisher="Press",
    )
    sync_state = get_sync_state()
    sync_state.remote_pages = [[record_payload("phase-request-c")], []]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )

    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    assert (
        payload["sync"]["message"]
        == "Creating book requests from the synced catalog records."
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/pause/",
    )
    assert payload["sync"]["status"] == "pausing"
    assert (
        payload["sync"]["message"]
        == "Pausing automated request creation after the current batch finishes."
    )

    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "paused"
    assert payload["sync"]["phase"] == "request_creation"
    assert payload["sync"]["progress"]["requestCreation"]["processedCount"] == 1
    assert payload["sync"]["progress"]["requestCreation"]["createdCount"] == 1

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/resume/",
        {"runMode": "catalog_automation"},
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    assert (
        payload["sync"]["message"]
        == "Resuming automated request creation from saved progress."
    )

    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["progress"]["requestCreation"]["processedCount"] == 2
    assert payload["sync"]["progress"]["requestCreation"]["createdCount"] == 2

    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "idle"
    assert BookCreationRequest.objects.filter(
        book_record_id="phase-request-a", state="initial"
    ).exists()
    assert BookCreationRequest.objects.filter(
        book_record_id="phase-request-b", state="initial"
    ).exists()
    assert BookCreationRequest.objects.filter(
        book_record_id="phase-request-c", state="initial"
    ).exists()
    assert payload["automation"]["catalog"]["statusMessage"] == "Created 3 requests."
