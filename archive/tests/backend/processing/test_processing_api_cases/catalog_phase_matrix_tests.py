

@pytest.mark.django_db
def test_catalog_automation_rerun_after_completion_starts_from_beginning(client):
    login_processing_admin(client)
    sync_state = get_sync_state()
    sync_state.remote_pages = [
        [record_payload("rerun-auto-page-1", name="Rerun Auto Page One")],
        [record_payload("rerun-auto-page-2", name="Rerun Auto Page Two")],
        [],
    ]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )

    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "syncing"
    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    payload = advance_processing_sync(client)
    assert payload["sync"]["status"] == "idle"
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "completed"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "completed"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "sync"
    assert payload["sync"]["pageIndex"] == 0
    assert payload["sync"]["fetchedCount"] == 0
    assert payload["sync"]["message"] == "Automated catalog sync is running."
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "running"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "not_started"
    assert "requestCreation" not in payload["sync"]["progress"]


@pytest.mark.django_db
@pytest.mark.parametrize("case", CATALOG_MANUAL_MATRIX_CASES)
def test_catalog_manual_matrix_rows(client, case):
    login_processing_admin(client)
    sync_state = get_sync_state()
    set_catalog_runtime_state(
        sync_state,
        sync_status=case["initial"]["sync_status"],
        request_creation_status=case["initial"]["request_creation_status"],
        top_status=case["initial"]["top_status"],
        sync_owner=case["initial"]["sync_owner"],
        request_creation_owner=case["initial"].get(
            "request_creation_owner",
            "catalog_automation",
        ),
        next_page_index=case["initial"].get("next_page_index", 1),
        fetched_count=case["initial"].get("fetched_count", 1),
        request_creation=case["initial"].get("request_creation"),
    )

    _mutation, payload = post_processing_mutation(
        client,
        case["action"]["path"],
        case["action"].get("body"),
    )

    assert_catalog_matrix_payload(payload, **case["expected"])


@pytest.mark.django_db
@pytest.mark.parametrize("case", CATALOG_AUTOMATION_MATRIX_CASES)
def test_catalog_automation_matrix_rows(client, case):
    login_processing_admin(client)
    sync_state = get_sync_state()
    set_catalog_runtime_state(
        sync_state,
        sync_status=case["initial"]["sync_status"],
        request_creation_status=case["initial"]["request_creation_status"],
        top_status=case["initial"]["top_status"],
        sync_owner=case["initial"]["sync_owner"],
        request_creation_owner=case["initial"].get(
            "request_creation_owner",
            "catalog_automation",
        ),
        next_page_index=case["initial"].get("next_page_index", 1),
        fetched_count=case["initial"].get("fetched_count", 1),
        request_creation=case["initial"].get("request_creation"),
    )

    _mutation, payload = post_processing_mutation(
        client,
        case["action"]["path"],
        case["action"].get("body"),
    )

    assert_catalog_matrix_payload(payload, **case["expected"])


@pytest.mark.django_db
def test_catalog_phase_one_pause_request_preserves_paused_phase_two_checkpoint(client):
    login_processing_admin(client)
    sync_state = get_sync_state()
    paused_request_creation = catalog_matrix_request_creation_payload(
        next_page_index=3,
        fetched_count=42,
        last_record_id="matrix-running-paused",
        processed_count=7,
        created_count=5,
    )
    set_catalog_runtime_state(
        sync_state,
        sync_status="running",
        request_creation_status="paused",
        top_status=ProcessingSyncStatus.SYNCING,
        sync_owner="manual",
        next_page_index=3,
        fetched_count=42,
        request_creation=paused_request_creation,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/catalog/pause/",
    )

    assert_catalog_matrix_payload(
        payload,
        status="pausing",
        phase="sync",
        run_mode="manual",
        sync_status="pausing",
        request_creation_status="paused",
        sync_owner="manual",
        request_creation_owner="catalog_automation",
        request_creation=paused_request_creation,
    )
    assert (
        payload["sync"]["progress"]["phaseStates"]["request_creation"][
            "baseSyncCheckpointToken"
        ]
        == paused_request_creation["baseCheckpointToken"]
    )


@pytest.mark.django_db
def test_catalog_phase_states_preserve_pausing_phase_one_and_paused_phase_two_checkpoints():
    sync_state = get_sync_state()
    paused_request_creation = catalog_matrix_request_creation_payload(
        next_page_index=4,
        fetched_count=12,
        last_record_id="matrix-pausing-paused",
        processed_count=3,
        created_count=2,
    )
    set_catalog_runtime_state(
        sync_state,
        sync_status="pausing",
        request_creation_status="paused",
        top_status=ProcessingSyncStatus.PAUSING,
        sync_owner="manual",
        next_page_index=4,
        fetched_count=12,
        request_creation=paused_request_creation,
    )

    payload = processing_services.serialize_sync_state(
        sync_state,
        include_remote_pages=False,
    )

    assert payload["status"] == "pausing"
    assert payload["progress"]["phaseStatuses"]["sync"] == "running"
    assert payload["progress"]["phaseStatuses"]["request_creation"] == "paused"
    assert payload["progress"]["phaseStates"]["sync"]["status"] == "pausing"
    assert payload["progress"]["phaseStates"]["sync"]["savedData"]["checkpointToken"] == (
        processing_services.catalog_sync_checkpoint_token(
            "catalog-matrix-session",
            next_page_index=4,
            fetched_count=12,
        )
    )
    assert payload["progress"]["phaseStates"]["request_creation"]["status"] == "paused"
    assert payload["progress"]["phaseStates"]["request_creation"][
        "baseSyncCheckpointToken"
    ] == paused_request_creation["baseCheckpointToken"]
    assert payload["progress"]["requestCreation"] == paused_request_creation


@pytest.mark.django_db
def test_catalog_automation_run_starts_request_creation_from_completed_sync_checkpoint(client):
    login_processing_admin(client)
    BookRecord.objects.create(
        id="matrix-phase-two-a",
        name="Matrix Phase Two A",
        url="https://example.test/books/matrix-phase-two-a",
        category="Reference",
        writer="Writer One",
        publisher="Press",
    )
    sync_state = get_sync_state()
    set_catalog_runtime_state(
        sync_state,
        sync_status="completed",
        request_creation_status="not_started",
        sync_owner="manual",
        next_page_index=1,
        fetched_count=1,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )

    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    assert payload["sync"]["message"] == "Creating book requests from the synced catalog records."
    assert payload["sync"]["progress"]["phaseStatuses"]["sync"] == "completed"
    assert payload["sync"]["progress"]["phaseStatuses"]["request_creation"] == "running"
    assert payload["sync"]["progress"]["phaseStates"]["request_creation"][
        "baseSyncCheckpointToken"
    ] == payload["sync"]["progress"]["requestCreation"]["baseCheckpointToken"]
