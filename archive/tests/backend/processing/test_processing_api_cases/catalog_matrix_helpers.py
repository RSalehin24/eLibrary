

def catalog_matrix_request_creation_payload(
    *,
    session_id="catalog-matrix-session",
    next_page_index=1,
    fetched_count=1,
    last_record_id="matrix-record-1",
    processed_count=1,
    created_count=1,
    unsupported_count=0,
):
    return {
        "baseCheckpointToken": processing_services.catalog_sync_checkpoint_token(
            session_id,
            next_page_index=next_page_index,
            fetched_count=fetched_count,
        ),
        "lastRecordId": last_record_id,
        "processedCount": processed_count,
        "createdCount": created_count,
        "unsupportedCount": unsupported_count,
    }


def assert_catalog_matrix_payload(
    payload,
    *,
    status,
    phase,
    run_mode,
    sync_status,
    request_creation_status,
    sync_owner=None,
    request_creation_owner=None,
    request_creation=None,
):
    compatibility_status = (
        lambda value: "running" if value == "pausing" else value
    )
    assert payload["sync"]["status"] == status
    assert payload["sync"]["phase"] == phase
    assert payload["sync"]["runMode"] == run_mode
    assert (
        payload["sync"]["progress"]["phaseStatuses"]["sync"]
        == compatibility_status(sync_status)
    )
    assert (
        payload["sync"]["progress"]["phaseStatuses"]["request_creation"]
        == compatibility_status(request_creation_status)
    )
    assert payload["sync"]["progress"]["phaseStates"]["sync"]["status"] == sync_status
    assert (
        payload["sync"]["progress"]["phaseStates"]["request_creation"]["status"]
        == request_creation_status
    )
    if sync_owner is not None:
        assert payload["sync"]["progress"]["phaseStates"]["sync"]["owner"] == sync_owner
    if request_creation_owner is not None:
        assert (
            payload["sync"]["progress"]["phaseStates"]["request_creation"]["owner"]
            == request_creation_owner
        )
    if request_creation is None:
        assert "requestCreation" not in payload["sync"]["progress"]
    else:
        assert payload["sync"]["progress"]["requestCreation"] == request_creation
