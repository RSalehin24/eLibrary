
from apps.processing.models import ProcessingSyncState


@pytest.mark.django_db
def test_processing_maintenance_requeues_stale_request_with_checkpoint():
    record = BookRecord.objects.create(
        id="stale-checkpoint-record",
        name="Stale Checkpoint Record",
        url="https://example.test/books/stale-checkpoint-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
    )
    request = BookCreationRequest.objects.create(
        id="stale-checkpoint-request",
        book_record=record,
        state="processing",
        progress={
            "checkpoint": "scraped-content",
            "savedData": {"scrapedData": {"title": "Saved Scrape"}},
        },
    )
    BookCreationRequest.objects.filter(pk=request.pk).update(
        updated_at=timezone.now() - timedelta(minutes=30)
    )

    result = processing_services.run_processing_maintenance()

    request.refresh_from_db()
    assert result["recoveredCount"] == 1
    assert request.state == "queued"
    assert request.is_resumed is True
    assert request.progress["savedData"]["scrapedData"]["title"] == "Saved Scrape"


@pytest.mark.django_db
def test_processing_maintenance_recovers_stale_sync_and_runtime_tick_resumes(monkeypatch):
    monkeypatch.setattr(
        "apps.processing.services.should_enqueue_processing_sync_work",
        lambda: False,
    )
    sync_state = get_sync_state()
    sync_state.status = ProcessingSyncStatus.SYNCING
    sync_state.remote_pages = [[record_payload("stale-sync-record")], []]
    sync_state.progress = {
        "runMode": "manual",
        "triggerSource": "button",
        "phase": "sync",
        "savedData": {"nextPageIndex": 0, "fetchedCount": 0},
    }
    sync_state.task_id = "lost-task"
    sync_state.queue_name = "processing"
    sync_state.save(
        update_fields=[
            "status",
            "remote_pages",
            "progress",
            "task_id",
            "queue_name",
            "updated_at",
        ]
    )
    ProcessingSyncState.objects.filter(pk=sync_state.pk).update(
        updated_at=timezone.now() - timedelta(minutes=30)
    )

    result = processing_services.run_processing_maintenance()

    sync_state.refresh_from_db()
    assert result["syncRecoveredCount"] == 1
    assert sync_state.status == ProcessingSyncStatus.SYNCING
    assert sync_state.task_id == ""
    assert sync_state.progress["savedData"]["nextPageIndex"] == 0

    processing_services.run_processing_runtime_tick()
    processing_services.run_processing_runtime_tick()
    assert BookRecord.objects.filter(pk="stale-sync-record").exists()
