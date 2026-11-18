

@pytest.mark.django_db
def test_processing_sync_serialization_repairs_stale_checkpoint_mirror(monkeypatch):
    fake_redis = FakeProcessingCheckpointRedis()
    monkeypatch.setattr(
        "apps.processing.services.processing_checkpoint_client",
        lambda: fake_redis,
    )

    sync_state = get_sync_state()
    sync_state.status = ProcessingSyncStatus.PAUSED
    sync_state.progress = {
        "runMode": "manual",
        "triggerSource": "button",
        "savedAt": timezone.now().isoformat(),
        "savedData": {
            "runMode": "manual",
            "triggerSource": "button",
            "nextPageIndex": 3,
            "fetchedCount": 42,
        },
    }
    sync_state.page_index = 3
    sync_state.fetched_count = 42
    sync_state.message = "Sync progress saved."
    sync_state.save(
        update_fields=[
            "status",
            "progress",
            "page_index",
            "fetched_count",
            "message",
            "updated_at",
        ]
    )

    checkpoint_key = processing_services.processing_sync_checkpoint_key("catalog")
    fake_redis.store[checkpoint_key] = json.dumps(
        {
            "scope": "catalog",
            "status": "paused",
            "runMode": "manual",
            "triggerSource": "button",
            "pageIndex": 1,
            "fetchedCount": 7,
            "progress": {
                "savedAt": "2000-01-01T00:00:00+00:00",
                "savedData": {"nextPageIndex": 1},
            },
        }
    )

    payload = processing_services.serialize_sync_state(
        sync_state,
        include_remote_pages=False,
    )
    processing_services.sync_checkpoint_progress(sync_state)

    assert payload["pageIndex"] == 3
    mirrored_payload = json.loads(fake_redis.store[checkpoint_key])
    assert mirrored_payload["pageIndex"] == 3
    assert mirrored_payload["fetchedCount"] == 42
    assert mirrored_payload["progress"]["savedData"]["nextPageIndex"] == 3


@pytest.mark.django_db
def test_processing_sync_checkpoint_mirror_clears_when_runtime_returns_to_idle(monkeypatch):
    fake_redis = FakeProcessingCheckpointRedis()
    monkeypatch.setattr(
        "apps.processing.services.processing_checkpoint_client",
        lambda: fake_redis,
    )

    processing_services.run_manual_catalog_sync(
        [[record_payload("mirror-stop-record")], []]
    )

    checkpoint_key = processing_services.processing_sync_checkpoint_key("catalog")
    assert checkpoint_key in fake_redis.store

    processing_services.stop_sync("catalog")

    assert checkpoint_key not in fake_redis.store


@pytest.mark.django_db
def test_processing_pipeline_does_not_reenqueue_queued_request_while_dispatch_is_pending(
    client, monkeypatch
):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="pending-dispatch-record",
        name="Pending Dispatch Record",
        url="https://example.test/books/pending-dispatch-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
    )
    dispatch_calls = []

    def fake_apply_async(*, args, **kwargs):
        dispatch_calls.append({"args": tuple(args), "kwargs": dict(kwargs)})
        return SimpleNamespace(id=f"task-{len(dispatch_calls)}")

    monkeypatch.setattr(
        "apps.processing.services.should_run_processing_jobs_inline",
        lambda: False,
    )
    monkeypatch.setattr(
        "apps.processing.services.processing_workers_available",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "apps.processing.tasks.kickoff_book_creation_request_task.apply_async",
        fake_apply_async,
    )

    response = client.post(
        "/api/processing/records/create-requests/",
        {"ids": [record.id]},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert dispatch_calls == [
        {
            "args": ("request-pending-dispatch-record",),
            "kwargs": {"queue": "processing"},
        }
    ]
    processing_request = BookCreationRequest.objects.get(book_record=record)
    assert processing_request.state == "queued"

    mutation, _payload = advance_processing_pipeline(client)

    assert mutation["advancedCount"] == 0
    processing_request.refresh_from_db()
    assert processing_request.state == "queued"

    mutation, _payload = advance_processing_pipeline(client)

    assert mutation["advancedCount"] == 0
    processing_request.refresh_from_db()
    assert processing_request.state == "queued"
    assert dispatch_calls == [
        {
            "args": ("request-pending-dispatch-record",),
            "kwargs": {"queue": "processing"},
        }
    ]


@pytest.mark.django_db
def test_processing_pipeline_dispatches_queued_request_even_with_initial_backlog(
    client, monkeypatch
):
    login_processing_admin(client)
    queued_record = BookRecord.objects.create(
        id="queued-backlog-record",
        name="Queued Backlog Record",
        url="https://example.test/books/queued-backlog-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="queued",
    )
    initial_record = BookRecord.objects.create(
        id="initial-backlog-record",
        name="Initial Backlog Record",
        url="https://example.test/books/initial-backlog-record",
        category="Fiction",
        writer="Writer Two",
        publisher="Example Press",
        book_creation_state="initial",
    )
    queued_request = BookCreationRequest.objects.create(
        id="queued-backlog-request",
        book_record=queued_record,
        state="queued",
    )
    initial_request = BookCreationRequest.objects.create(
        id="initial-backlog-request",
        book_record=initial_record,
        state="initial",
    )
    dispatch_calls = []

    def fake_apply_async(*, args, **kwargs):
        dispatch_calls.append({"args": tuple(args), "kwargs": dict(kwargs)})
        return SimpleNamespace(id=f"task-{len(dispatch_calls)}")

    monkeypatch.setattr(
        "apps.processing.services.should_run_processing_jobs_inline",
        lambda: False,
    )
    monkeypatch.setattr(
        "apps.processing.services.processing_workers_available",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "apps.processing.tasks.kickoff_book_creation_request_task.apply_async",
        fake_apply_async,
    )

    mutation, _payload = advance_processing_pipeline(client)

    assert mutation["advancedCount"] == 2
    queued_request.refresh_from_db()
    initial_request.refresh_from_db()
    assert queued_request.state == "queued"
    assert initial_request.state == "queued"
    assert dispatch_calls == [
        {
            "args": ("queued-backlog-request",),
            "kwargs": {"queue": "processing"},
        }
    ]
