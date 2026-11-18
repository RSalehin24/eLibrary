

@pytest.mark.django_db
def test_processing_table_keeps_on_hold_cards_scoped_to_request_status(client):
    login_processing_admin(client)

    card_states = {
        "on-hold-paused": "paused",
        "on-hold-failed": "failed",
        "on-hold-duplicate": "duplicate",
        "on-hold-deleted": "deleted",
    }
    request_ids = {}

    for card_id, status in card_states.items():
        record = BookRecord.objects.create(
            id=f"{card_id}-record",
            name=f"{card_id} title",
            url=f"https://example.test/books/{card_id}",
            category="Reference",
            writer="Writer One",
            publisher="Example Press",
            book_creation_state=status,
        )
        request = BookCreationRequest.objects.create(
            id=f"{card_id}-request",
            book_record=record,
            state=status,
        )
        request_ids[card_id] = str(request.id)

    for card_id, status in card_states.items():
        response = client.get(f"/api/processing/table/?card={card_id}")

        assert response.status_code == 200
        payload = response.json()
        assert [row["requestId"] for row in payload["rows"]] == [request_ids[card_id]]
        assert {row["status"] for row in payload["rows"]} == {status}
        assert payload["filters"]["statusOptions"] == [status]


@pytest.mark.django_db
def test_catalog_automation_waits_for_manual_runtime_before_creating_requests(client):
    login_processing_admin(client)
    BookRecord.objects.create(
        id="existing-record",
        name="Existing Record",
        url="https://example.test/books/existing-record",
        category="History",
        writer="Writer One",
        publisher="Example Press",
    )

    response = client.post(
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [
                    record_payload(
                        "existing-record",
                        name="Existing Record Revised",
                        category="Updated",
                    )
                ],
                [record_payload("new-record", name="New Record", category="Poetry")],
                [],
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert not BookRecord.objects.filter(pk="new-record").exists()

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "manual"
    assert not BookCreationRequest.objects.exists()

    payload = advance_processing_sync(client, count=2)
    assert payload["sync"]["status"] == "idle"
    assert BookRecord.objects.filter(pk="new-record").exists()
    assert BookRecord.objects.get(pk="existing-record").name == "Existing Record Revised"
    assert not BookCreationRequest.objects.exists()

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "catalog_automation"

    payload = advance_processing_sync(client, count=3)
    assert payload["sync"]["status"] == "idle"
    assert BookCreationRequest.objects.filter(
        book_record_id="existing-record",
        state="initial",
    ).exists()
    assert BookCreationRequest.objects.filter(
        book_record_id="new-record",
        state="initial",
    ).exists()
    assert payload["automation"]["catalog"]["statusMessage"] == "Created 2 requests."


@pytest.mark.django_db
def test_processing_sync_start_ignores_remote_pages_when_overrides_are_disabled(client, monkeypatch):
    login_processing_admin(client)
    monkeypatch.setattr(
        "apps.processing.views.allow_processing_remote_page_payloads",
        lambda: False,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
        {"remotePages": [[record_payload("ignored-record")], []]},
    )
    assert payload["sync"]["status"] == "syncing"

    payload = advance_processing_sync(client, count=2)
    assert payload["sync"]["status"] == "idle"
    assert not BookRecord.objects.filter(pk="ignored-record").exists()


@pytest.mark.django_db
def test_catalog_automation_ignores_stale_remote_pages_when_overrides_are_disabled(client, monkeypatch):
    login_processing_admin(client)
    monkeypatch.setattr(
        "apps.processing.services.allow_processing_remote_page_payloads",
        lambda: False,
    )

    sync_state = get_sync_state()
    sync_state.remote_pages = [[record_payload("stale-remote-record")], []]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    entry = SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/fallback-live-record/",
        title="Fallback Live Record",
        author_line="Source Author",
        normalized_title="fallback live record",
        normalized_display="fallback live record source author",
        raw_data={"category": "Fallback Category", "publisher": "Source Publisher"},
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
    assert not BookRecord.objects.filter(pk="stale-remote-record").exists()
    assert BookRecord.objects.filter(pk=str(entry.id)).exists()

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "idle"
    assert BookCreationRequest.objects.filter(
        book_record_id=str(entry.id),
        state="initial",
    ).exists()


@pytest.mark.django_db
def test_catalog_automation_can_pause_and_stop_active_sync(client):
    login_processing_admin(client)
    sync_state = get_sync_state()
    sync_state.remote_pages = [
        [record_payload("auto-page-1", name="Automation Page One")],
        [record_payload("auto-page-2", name="Automation Page Two")],
        [],
    ]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
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

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/resume/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "catalog_automation"
    assert payload["sync"]["message"] == "Continuing automated catalog sync from the saved endpoint."
    assert payload["sync"]["pageIndex"] == 1

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/stop/",
    )
    assert payload["sync"]["status"] == "idle"
    assert payload["sync"]["message"] == "Automated catalog sync stopped."
    assert payload["automation"]["catalog"]["statusMessage"] == "Automated catalog sync stopped."
