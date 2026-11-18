

@pytest.mark.django_db
@pytest.mark.parametrize(
    "read_path",
    [
        "/api/processing/state/?includeLists=0",
        "/api/processing/table/?card=catalog-records",
        "/api/processing/card/?card=catalog-sync",
    ],
)
def test_processing_get_endpoints_do_not_advance_pausing_sync(client, read_path):
    login_processing_admin(client)

    start_response = client.post(
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [record_payload("read-only-pausing-sync-record")],
                [],
            ],
        },
        content_type="application/json",
    )
    assert start_response.status_code == 200

    pause_response = client.post(
        "/api/processing/sync/catalog/pause/",
        {},
        content_type="application/json",
    )
    assert pause_response.status_code == 200

    sync_state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    assert sync_state.status == ProcessingSyncStatus.PAUSING

    response = client.get(read_path)

    assert response.status_code == 200
    sync_state.refresh_from_db()
    assert sync_state.status == ProcessingSyncStatus.PAUSING
    assert not BookRecord.objects.filter(pk="read-only-pausing-sync-record").exists()


@pytest.mark.django_db
def test_processing_state_does_not_run_due_automations(client, monkeypatch):
    login_processing_admin(client)
    scheduled_time = timezone.localtime(timezone.now()).replace(
        second=0,
        microsecond=0,
    ).time()
    ProcessingAutomationSettings.objects.update_or_create(
        kind=ProcessingAutomationKind.CATALOG,
        defaults={
            "enabled": True,
            "interval": "daily",
            "time": scheduled_time,
            "saved": True,
            "last_run_at": None,
            "status_message": "",
        },
    )
    monkeypatch.setattr(
        "apps.processing.services.should_run_processing_jobs_inline",
        lambda: False,
    )
    monkeypatch.setattr(
        "apps.processing.services.should_enqueue_processing_sync_work",
        lambda: False,
    )

    response = client.get("/api/processing/state/?includeLists=0")

    assert response.status_code == 200
    sync_state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    assert sync_state.status == ProcessingSyncStatus.IDLE
    automation_settings = ProcessingAutomationSettings.objects.get(
        kind=ProcessingAutomationKind.CATALOG,
    )
    assert automation_settings.last_run_at is None
    assert automation_settings.status_message == ""
