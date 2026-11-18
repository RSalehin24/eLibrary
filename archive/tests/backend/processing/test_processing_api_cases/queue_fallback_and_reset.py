

@pytest.mark.django_db
def test_processing_create_requests_dispatches_without_worker_probe(client, monkeypatch):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="probe-free-dispatch-record",
        name="Probe Free Dispatch Record",
        url="https://example.test/books/probe-free-dispatch-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
    )
    dispatch_calls = []

    def fake_apply_async(*, args, **kwargs):
        dispatch_calls.append({"args": tuple(args), "kwargs": dict(kwargs)})
        return SimpleNamespace(id="probe-free-task")

    monkeypatch.setattr(
        "apps.processing.services.should_run_processing_jobs_inline",
        lambda: False,
    )
    monkeypatch.setattr(
        "apps.processing.services.processing_workers_available",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
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
    processing_request = BookCreationRequest.objects.get(book_record=record)
    assert processing_request.state == "queued"
    assert processing_request.progress["_dispatchTaskId"] == "probe-free-task"
    assert dispatch_calls == [
        {
            "args": ("request-probe-free-dispatch-record",),
            "kwargs": {"queue": "processing"},
        }
    ]


@pytest.mark.django_db
def test_processing_pipeline_falls_back_to_inline_when_dispatch_fails(
    client, monkeypatch
):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="dispatch-failure-record",
        name="Dispatch Failure Record",
        url="https://example.test/books/dispatch-failure-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="queued",
    )
    processing_request = BookCreationRequest.objects.create(
        id="dispatch-failure-request",
        book_record=record,
        state="queued",
    )

    def fake_run_processing_request(request):
        request.state = "created"
        request.error_message = ""
        request.save(update_fields=["state", "error_message", "updated_at"])
        processing_services.sync_record_state(request.book_record)
        return request

    monkeypatch.setattr(
        "apps.processing.services.should_run_processing_jobs_inline",
        lambda: False,
    )
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        "apps.processing.tasks.kickoff_book_creation_request_task.apply_async",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("broker unavailable")),
    )
    monkeypatch.setattr(
        "apps.processing.services._run_processing_request",
        fake_run_processing_request,
    )

    mutation, _payload = advance_processing_pipeline(client)

    assert mutation["advancedCount"] == 1
    processing_request.refresh_from_db()
    record.refresh_from_db()
    assert processing_request.state == "created"
    assert record.book_creation_state == "created"


@pytest.mark.django_db
def test_processing_pipeline_requeues_stale_dispatch_marker(client, monkeypatch):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="stale-dispatch-record",
        name="Stale Dispatch Record",
        url="https://example.test/books/stale-dispatch-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="queued",
    )
    processing_request = BookCreationRequest.objects.create(
        id="stale-dispatch-request",
        book_record=record,
        state="queued",
        progress={
            "_dispatchRequestedAt": (
                timezone.now() - timedelta(minutes=5)
            ).isoformat(),
            "_dispatchTaskId": "stale-processing-task",
        },
    )
    dispatch_calls = []

    def fake_apply_async(*, args, **kwargs):
        dispatch_calls.append({"args": tuple(args), "kwargs": dict(kwargs)})
        return SimpleNamespace(id="fresh-processing-task")

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

    assert mutation["advancedCount"] == 1
    processing_request.refresh_from_db()
    assert processing_request.state == "queued"
    assert processing_request.progress["_dispatchTaskId"] == "fresh-processing-task"
    assert dispatch_calls == [
        {
            "args": ("stale-dispatch-request",),
            "kwargs": {"queue": "processing"},
        }
    ]


@pytest.mark.django_db
def test_processing_sync_dispatches_to_processing_queue(monkeypatch):
    sync_state = get_sync_state()
    sync_state.status = ProcessingSyncStatus.SYNCING
    sync_state.task_id = ""
    sync_state.queue_name = ""
    sync_state.last_error = "stale error"
    sync_state.save(update_fields=["status", "task_id", "queue_name", "last_error", "updated_at"])

    dispatch_calls = []

    def fake_apply_async(*, args, **kwargs):
        dispatch_calls.append({"args": tuple(args), "kwargs": dict(kwargs)})
        return SimpleNamespace(id=kwargs.get("task_id"))

    monkeypatch.setattr(
        "apps.processing.tasks.run_processing_sync_task.apply_async",
        fake_apply_async,
    )

    dispatch_sync_task(sync_state, force=True)

    sync_state.refresh_from_db()
    assert sync_state.queue_name == "processing"
    assert sync_state.last_error == ""
    assert len(dispatch_calls) == 1
    assert dispatch_calls[0]["args"] == ("catalog",)
    assert dispatch_calls[0]["kwargs"]["queue"] == "processing"
    assert dispatch_calls[0]["kwargs"]["task_id"] == sync_state.task_id


@pytest.mark.django_db
def test_reset_processing_data_can_revoke_tasks_and_purge_processing_queue(
    monkeypatch,
):
    record = BookRecord.objects.create(
        id="reset-processing-record",
        name="Reset Processing Record",
        url="https://example.test/books/reset-processing-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="queued",
    )
    BookCreationRequest.objects.create(
        id="reset-processing-request",
        book_record=record,
        state="queued",
        progress={
            processing_services.PROCESSING_DISPATCH_TASK_ID_KEY: "request-task-id",
        },
    )
    sync_state = get_sync_state()
    sync_state.status = ProcessingSyncStatus.SYNCING
    sync_state.task_id = "sync-task-id"
    sync_state.queue_name = "processing"
    sync_state.save(update_fields=["status", "task_id", "queue_name", "updated_at"])

    revoked = []
    purged = []

    monkeypatch.setattr(
        processing_services.celery_app.control,
        "revoke",
        lambda task_id, terminate=False: revoked.append((task_id, terminate)),
    )
    monkeypatch.setattr(
        processing_services,
        "purge_processing_task_queue",
        lambda: purged.append(True) or 1,
    )

    processing_services.reset_processing_data(revoke_tasks=True, purge_queue=True)

    record.refresh_from_db()
    sync_state.refresh_from_db()
    assert {task_id for task_id, _terminate in revoked} == {
        "request-task-id",
        "sync-task-id",
    }
    assert purged == [True]
    assert BookCreationRequest.objects.count() == 0
    assert record.book_creation_state == "not_created"
    assert sync_state.status == ProcessingSyncStatus.IDLE
    assert sync_state.task_id == ""
    assert sync_state.queue_name == ""
