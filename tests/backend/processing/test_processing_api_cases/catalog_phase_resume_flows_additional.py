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
def test_manual_start_from_paused_automation_request_creation_preserves_phase_two_checkpoint(
    client,
    monkeypatch,
):
    login_processing_admin(client)
    monkeypatch.setattr(
        "apps.processing.service_modules.service_imports_and_constants.CATALOG_REQUEST_CREATION_BATCH_SIZE",
        1,
    )
    BookRecord.objects.create(
        id="carry-existing",
        name="Carry Existing",
        url="https://example.test/books/carry-existing",
        category="Reference",
        writer="Writer One",
        publisher="Press",
    )
    sync_state = get_sync_state()
    sync_state.remote_pages = [[record_payload("carry-new")], []]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )

    payload = advance_processing_sync(client)
    assert payload["sync"]["phase"] == "request_creation"

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/sync/pause/",
    )
    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "paused"
    assert payload["sync"]["progress"]["requestCreation"]["processedCount"] == 1
    paused_request_creation_base_token = payload["sync"]["progress"]["phaseStates"][
        "request_creation"
    ]["baseSyncCheckpointToken"]

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
        {"remotePages": [[record_payload("carry-new")], []]},
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "manual"
    assert payload["sync"]["message"] == "Syncing catalog records."
    assert payload["sync"]["pageIndex"] == 0
    assert payload["sync"]["fetchedCount"] == 0
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "running"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "paused"
    assert payload["sync"]["progress"]["requestCreation"]["processedCount"] == 1
    assert (
        payload["sync"]["progress"]["phaseStates"]["request_creation"]["status"]
        == "paused"
    )

    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "paused"
    assert payload["sync"]["message"].startswith("Sync complete.")
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "completed"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "paused"
    assert payload["sync"]["progress"]["requestCreation"]["processedCount"] == 1
    completed_sync_checkpoint_token = payload["sync"]["progress"]["phaseStates"][
        "sync"
    ]["savedData"]["checkpointToken"]
    assert completed_sync_checkpoint_token != paused_request_creation_base_token
    assert (
        payload["sync"]["progress"]["phaseStates"]["request_creation"][
            "baseSyncCheckpointToken"
        ]
        == paused_request_creation_base_token
    )
    assert BookCreationRequest.objects.count() == 1

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    assert (
        payload["sync"]["message"]
        == "Resuming automated request creation from saved progress."
    )
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "completed"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "running"
    assert (
        payload["sync"]["progress"]["phaseStates"]["request_creation"][
            "baseSyncCheckpointToken"
        ]
        == paused_request_creation_base_token
    )
    assert (
        payload["sync"]["progress"]["requestCreation"]["baseCheckpointToken"]
        == paused_request_creation_base_token
    )

    payload = advance_processing_sync(client, count=2)
    assert payload["sync"]["status"] == "idle"
    assert BookCreationRequest.objects.count() == 2
