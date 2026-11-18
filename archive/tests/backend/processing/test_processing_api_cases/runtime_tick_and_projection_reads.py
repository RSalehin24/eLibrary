

@pytest.mark.django_db
def test_processing_stream_emits_versions_without_advancing_sync(client, monkeypatch):
    login_processing_admin(client)

    start_response = client.post(
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [record_payload("stream-sync-record")],
                [],
            ]
        },
        content_type="application/json",
    )

    assert start_response.status_code == 200

    monkeypatch.setattr("apps.processing.views.time.sleep", lambda _seconds: None)
    diff_calls = {"count": 0}

    def fake_versions_diff(previous_versions, *, domains=None):
        diff_calls["count"] += 1
        if diff_calls["count"] == 1:
            next_versions = dict(previous_versions)
            next_versions["catalog-sync"] = 1
            return {"catalog-sync": 1}, next_versions
        raise GeneratorExit

    monkeypatch.setattr(
        "apps.processing.views.processing_ui_versions_diff",
        fake_versions_diff,
    )

    response = client.get("/api/processing/stream/?page=catalog")

    assert response.status_code == 200
    stream = iter(response.streaming_content)
    assert next(stream).decode() == "event: connected\ndata: {}\n\n"

    versions_event = next(stream).decode()
    assert "event: versions" in versions_event
    payload = json.loads(versions_event.split("data: ", 1)[1])
    assert payload["versions"] == {"catalog-sync": 1}

    sync_state = get_sync_state()
    assert sync_state.status == "syncing"
    assert not BookRecord.objects.filter(pk="stream-sync-record").exists()


@pytest.mark.django_db
def test_processing_runtime_tick_advances_sync_and_pipeline_without_browser(client, monkeypatch):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="runtime-tick-request-record",
        name="Runtime Tick Request Record",
        url="https://www.example.com/books/runtime-tick-request-record/",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
    )
    BookCreationRequest.objects.create(
        id="runtime-tick-request",
        book_record=record,
        state="initial",
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [record_payload("runtime-tick-sync-record")],
                [],
            ]
        },
    )
    assert payload["sync"]["status"] == "syncing"

    monkeypatch.setattr(
        "apps.processing.services.should_run_processing_jobs_inline",
        lambda: False,
    )
    monkeypatch.setattr(
        "apps.processing.services.processing_workers_available",
        lambda *_args, **_kwargs: False,
    )

    result = processing_services.run_processing_runtime_tick()

    sync_state = get_sync_state()
    processing_request = BookCreationRequest.objects.get(pk="runtime-tick-request")
    synced_record = BookRecord.objects.get(pk="runtime-tick-sync-record")

    assert result["advancedCount"] == 1
    assert result["sync"]["catalog"]["status"] == "idle"
    assert sync_state.status == "idle"
    assert synced_record.name == "runtime-tick-sync-record title"
    assert processing_request.state == "queued"


@pytest.mark.django_db
def test_processing_state_does_not_advance_processing_pipeline(client, monkeypatch):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="read-only-pipeline-record",
        name="Read Only Pipeline Record",
        url="https://example.test/books/read-only-pipeline-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="processing",
    )
    processing_request = BookCreationRequest.objects.create(
        id="read-only-pipeline-request",
        book_record=record,
        state="processing",
    )
    run_calls = {"count": 0}

    monkeypatch.setattr(
        "apps.processing.services._run_processing_request",
        lambda request: run_calls.__setitem__("count", run_calls["count"] + 1),
    )

    response = client.get("/api/processing/state/?includeLists=0")

    assert response.status_code == 200
    processing_request.refresh_from_db()
    record.refresh_from_db()
    assert run_calls["count"] == 0
    assert processing_request.state == "processing"
    assert record.book_creation_state == "processing"


@pytest.mark.django_db
def test_processing_table_does_not_advance_processing_pipeline(client, monkeypatch):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="read-only-table-record",
        name="Read Only Table Record",
        url="https://example.test/books/read-only-table-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="processing",
    )
    processing_request = BookCreationRequest.objects.create(
        id="read-only-table-request",
        book_record=record,
        state="processing",
    )
    run_calls = {"count": 0}

    monkeypatch.setattr(
        "apps.processing.services._run_processing_request",
        lambda request: run_calls.__setitem__("count", run_calls["count"] + 1),
    )

    response = client.get("/api/processing/table/?card=create-processing")

    assert response.status_code == 200
    processing_request.refresh_from_db()
    record.refresh_from_db()
    assert run_calls["count"] == 0
    assert processing_request.state == "processing"
    assert record.book_creation_state == "processing"


@pytest.mark.django_db
def test_processing_state_reads_primary_sync_from_projection_rows_only(monkeypatch):
    rebuild_processing_ui_state()

    catalog_projection = processing_services.ProcessingUiProjection.objects.get(
        key="catalog-sync"
    )
    incomplete_projection = processing_services.ProcessingUiProjection.objects.get(
        key="incomplete-automation"
    )
    catalog_payload = {
        **catalog_projection.payload,
        "sync": {
            **catalog_projection.payload["sync"],
            "status": "idle",
            "message": "Catalog idle first.",
        },
    }
    incomplete_payload = {
        **incomplete_projection.payload,
        "sync": {
            **incomplete_projection.payload["sync"],
            "status": "idle",
            "message": "Incomplete idle last.",
            "runMode": "incomplete_automation",
            "scope": "incomplete",
        },
    }
    now = timezone.now()
    processing_services.ProcessingUiProjection.objects.filter(
        pk=catalog_projection.pk
    ).update(payload=catalog_payload, updated_at=now - timedelta(minutes=2))
    processing_services.ProcessingUiProjection.objects.filter(
        pk=incomplete_projection.pk
    ).update(payload=incomplete_payload, updated_at=now - timedelta(minutes=1))

    monkeypatch.setattr(
        "apps.processing.services.processing_shared_projection_payloads",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("processing state should not rebuild shared projections")
        ),
    )

    payload = processing_services.processing_state_payload(include_lists=False)
    assert payload["sync"]["scope"] == "incomplete"
    assert payload["sync"]["message"] == "Incomplete idle last."


@pytest.mark.django_db
def test_save_sync_state_catalog_publishes_only_catalog_sync_domain(
    django_capture_on_commit_callbacks,
):
    state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    previous_versions = processing_services.processing_ui_versions_map(
        domains=["catalog-sync", "catalog-automation"]
    )

    state.status = ProcessingSyncStatus.SYNCING
    state.message = "Catalog sync is running."
    with django_capture_on_commit_callbacks(execute=True):
        processing_services.save_sync_state(state)

    current_versions = processing_services.processing_ui_versions_map(
        domains=["catalog-sync", "catalog-automation"]
    )
    assert current_versions["catalog-sync"] == previous_versions["catalog-sync"] + 1
    assert current_versions["catalog-automation"] == previous_versions["catalog-automation"]
