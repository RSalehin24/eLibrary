

@pytest.mark.django_db
def test_manual_and_automation_can_resume_different_paused_catalog_phases(client):
    login_processing_admin(client)
    sync_state = get_sync_state()
    sync_state.remote_pages = [
        [record_payload("matrix-paused-phase-1", name="Matrix Paused Phase 1")],
        [],
    ]
    sync_state.save(update_fields=["remote_pages", "updated_at"])
    paused_request_creation = {
        "baseCheckpointToken": processing_services.catalog_sync_checkpoint_token(
            "catalog-matrix-session",
            next_page_index=1,
            fetched_count=1,
        ),
        "lastRecordId": "matrix-record-1",
        "processedCount": 1,
        "createdCount": 1,
        "unsupportedCount": 0,
    }
    set_catalog_runtime_state(
        sync_state,
        sync_status="paused",
        request_creation_status="paused",
        sync_owner="manual",
        request_creation=paused_request_creation,
        next_page_index=1,
        fetched_count=1,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "sync"
    assert payload["sync"]["runMode"] == "manual"
    assert payload["sync"]["message"] == "Continuing catalog sync from the saved endpoint."
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "running"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "paused"
    assert payload["sync"]["progress"]["requestCreation"] == paused_request_creation

    set_catalog_runtime_state(
        sync_state,
        sync_status="paused",
        request_creation_status="paused",
        sync_owner="manual",
        request_creation=paused_request_creation,
        next_page_index=1,
        fetched_count=1,
    )
    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    assert payload["sync"]["runMode"] == "catalog_automation"
    assert payload["sync"]["message"] == "Resuming automated request creation from saved progress."
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "paused"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "running"


@pytest.mark.django_db
def test_processing_sync_serialization_normalizes_legacy_catalog_progress_into_phase_states():
    sync_state = get_sync_state()
    sync_state.status = ProcessingSyncStatus.PAUSED
    sync_state.progress = {
        "runMode": "catalog_automation",
        "triggerSource": "button",
        "phase": "request_creation",
        "checkpoint": "request-1",
        "savedAt": timezone.now().isoformat(),
        "savedData": {
            "runMode": "catalog_automation",
            "triggerSource": "button",
            "sessionId": "legacy-catalog-session",
            "checkpointToken": "legacy-catalog-session:0:1:1",
            "nextPageIndex": 1,
            "fetchedCount": 1,
        },
        "requestCreation": {
            "baseCheckpointToken": "legacy-catalog-session:0:1:1",
            "lastRecordId": "legacy-record-1",
            "processedCount": 1,
            "createdCount": 1,
            "unsupportedCount": 0,
        },
    }
    sync_state.page_index = 1
    sync_state.fetched_count = 1
    sync_state.save(
        update_fields=[
            "status",
            "progress",
            "page_index",
            "fetched_count",
            "updated_at",
        ]
    )

    payload = processing_services.serialize_sync_state(sync_state, include_remote_pages=False)

    assert payload["progress"]["phaseStatuses"]["sync"] == "completed"
    assert payload["progress"]["phaseStatuses"]["request_creation"] == "paused"
    assert payload["progress"]["phaseStates"]["sync"]["status"] == "completed"
    assert payload["progress"]["phaseStates"]["request_creation"]["status"] == "paused"
    assert payload["progress"]["phaseStates"]["request_creation"][
        "baseSyncCheckpointToken"
    ] == "legacy-catalog-session:0:1:1"


@pytest.mark.django_db
def test_processing_sync_serialization_normalizes_legacy_catalog_pausing_progress():
    sync_state = get_sync_state()
    saved_at = timezone.now().isoformat()
    sync_state.status = ProcessingSyncStatus.PAUSING
    sync_state.progress = {
        "runMode": "manual",
        "triggerSource": "button",
        "phase": "sync",
        "checkpoint": "page-2",
        "savedData": {
            "runMode": "manual",
            "triggerSource": "button",
            "sessionId": "legacy-catalog-pausing",
            "checkpointToken": "legacy-catalog-pausing:0:2:8",
            "nextPageIndex": 2,
            "fetchedCount": 8,
        },
        "phaseStatuses": {
            "sync": "running",
            "request_creation": "paused",
        },
        "requestCreation": {
            "baseCheckpointToken": "legacy-catalog-pausing:0:1:4",
            "lastRecordId": "legacy-paused-request",
            "processedCount": 4,
            "createdCount": 2,
            "unsupportedCount": 0,
        },
        "savedAt": saved_at,
    }
    sync_state.page_index = 2
    sync_state.fetched_count = 8
    sync_state.save(
        update_fields=[
            "status",
            "progress",
            "page_index",
            "fetched_count",
            "updated_at",
        ]
    )

    payload = processing_services.serialize_sync_state(sync_state, include_remote_pages=False)

    assert payload["status"] == "pausing"
    assert payload["progress"]["phaseStatuses"]["sync"] == "running"
    assert payload["progress"]["phaseStatuses"]["request_creation"] == "paused"
    assert payload["progress"]["phaseStates"]["sync"]["status"] == "pausing"
    assert payload["progress"]["phaseStates"]["sync"]["savedAt"] == saved_at
    assert payload["progress"]["phaseStates"]["request_creation"]["status"] == "paused"
    assert payload["progress"]["phaseStates"]["request_creation"][
        "baseSyncCheckpointToken"
    ] == "legacy-catalog-pausing:0:1:4"
