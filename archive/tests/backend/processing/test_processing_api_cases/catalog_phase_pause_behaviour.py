

@pytest.mark.django_db
@pytest.mark.parametrize(
    ("progress_phase", "expected_sync_status", "expected_request_creation_status"),
    [
        (
            "sync",
            "running",
            "paused",
        ),
        (
            "request_creation",
            "completed",
            "running",
        ),
    ],
)
def test_processing_sync_serialization_normalizes_dual_active_catalog_phase_states(
    progress_phase,
    expected_sync_status,
    expected_request_creation_status,
):
    sync_state = get_sync_state()
    session_id = "dual-active-session"
    checkpoint_token = processing_services.catalog_sync_checkpoint_token(
        session_id,
        next_page_index=2,
        fetched_count=8,
    )
    request_creation = {
        "baseCheckpointToken": checkpoint_token,
        "lastRecordId": "dual-active-record",
        "processedCount": 3,
        "createdCount": 2,
        "unsupportedCount": 0,
    }
    sync_state.status = ProcessingSyncStatus.SYNCING
    sync_state.progress = {
        "runMode": "catalog_automation",
        "triggerSource": "button",
        "phase": progress_phase,
        "phaseStatuses": {
            "sync": "running",
            "request_creation": "running",
        },
        "phaseStates": {
            "sync": processing_services._catalog_phase_state(
                processing_services.CATALOG_SYNC_PHASE,
                status="running",
                owner="manual",
                trigger_source=processing_services.SYNC_TRIGGER_SOURCE_BUTTON,
                checkpoint="page-2",
                saved_data={
                    "runMode": "manual",
                    "triggerSource": "button",
                    "sessionId": session_id,
                    "checkpointToken": checkpoint_token,
                    "nextPageIndex": 2,
                    "fetchedCount": 8,
                },
            ),
            "request_creation": processing_services._catalog_phase_state(
                processing_services.CATALOG_REQUEST_CREATION_PHASE,
                status="running",
                owner="catalog_automation",
                trigger_source=processing_services.SYNC_TRIGGER_SOURCE_BUTTON,
                checkpoint="request-dual-active-record",
                request_creation=request_creation,
                base_sync_checkpoint_token=checkpoint_token,
            ),
        },
        "savedData": {
            "runMode": "manual",
            "triggerSource": "button",
            "sessionId": session_id,
            "checkpointToken": checkpoint_token,
            "nextPageIndex": 2,
            "fetchedCount": 8,
        },
        "requestCreation": request_creation,
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

    assert payload["progress"]["phaseStates"]["sync"]["status"] == expected_sync_status
    assert (
        payload["progress"]["phaseStates"]["request_creation"]["status"]
        == expected_request_creation_status
    )
    assert (
        payload["progress"]["phaseStatuses"]["sync"]
        == ("running" if expected_sync_status == "pausing" else expected_sync_status)
    )
    assert (
        payload["progress"]["phaseStatuses"]["request_creation"]
        == (
            "running"
            if expected_request_creation_status == "pausing"
            else expected_request_creation_status
        )
    )


@pytest.mark.django_db
def test_processing_sync_honors_pause_requested_during_page_advance(client, monkeypatch):
    login_processing_admin(client)

    response = client.post(
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [record_payload("mid-page-pause-a")],
                [record_payload("mid-page-pause-b")],
                [],
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 200

    original_upsert = processing_services.upsert_remote_records

    def pause_after_upsert(*args, **kwargs):
        result = original_upsert(*args, **kwargs)
        processing_services.pause_sync()
        return result

    monkeypatch.setattr(
        "apps.processing.services.upsert_remote_records",
        pause_after_upsert,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "paused"
    assert payload["sync"]["progress"]["savedData"]["nextPageIndex"] == 1
    assert payload["sync"]["fetchedCount"] == 1
    assert BookRecord.objects.filter(pk="mid-page-pause-a").exists()
    assert not BookRecord.objects.filter(pk="mid-page-pause-b").exists()


@pytest.mark.django_db
def test_incomplete_sync_honors_pause_requested_during_batch_advance(client, monkeypatch):
    login_processing_admin(client)
    BookRecord.objects.create(
        id="mid-incomplete-a",
        name="Mid Incomplete A",
        url="https://example.test/books/mid-incomplete-a",
        category="অসম্পূর্ণ বই",
        writer="Writer One",
        publisher="Example Press",
        was_incomplete=True,
        resolved_from_incomplete=False,
        will_resolve_to_category="Novel",
    )
    BookRecord.objects.create(
        id="mid-incomplete-b",
        name="Mid Incomplete B",
        url="https://example.test/books/mid-incomplete-b",
        category="অসম্পূর্ণ বই",
        writer="Writer Two",
        publisher="Example Press",
        was_incomplete=True,
        resolved_from_incomplete=False,
        will_resolve_to_category="Novel",
    )

    response = client.post(
        "/api/processing/automation/incomplete/run/",
        content_type="application/json",
    )

    assert response.status_code == 200
    sync_state = get_sync_state(PROCESSING_SYNC_KEY_INCOMPLETE)
    sync_state.remote_pages = [["mid-incomplete-a"], ["mid-incomplete-b"], []]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    original_resolve = processing_services.resolve_incomplete_records

    def pause_after_resolve(*args, **kwargs):
        resolved = original_resolve(*args, **kwargs)
        processing_services.pause_sync()
        return resolved

    monkeypatch.setattr(
        "apps.processing.services.resolve_incomplete_records",
        pause_after_resolve,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "paused"
    assert payload["sync"]["runMode"] == "incomplete_automation"
    assert payload["sync"]["progress"]["savedData"]["nextPageIndex"] == 1
    assert payload["sync"]["updatedCount"] == 1
    assert BookRecord.objects.get(pk="mid-incomplete-a").resolved_from_incomplete is True
    assert BookRecord.objects.get(pk="mid-incomplete-b").resolved_from_incomplete is False
