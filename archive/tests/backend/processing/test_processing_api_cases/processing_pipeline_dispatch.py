

@pytest.mark.django_db
def test_catalog_automation_ignores_incomplete_remote_pages_shape(client):
    login_processing_admin(client)
    entry = SourceCatalogEntry.objects.create(
        source_url="https://example.test/books/catalog-fallback-record",
        title="Catalog Fallback Record",
        author_line="Source Author",
        normalized_title="catalog fallback record",
        normalized_display="catalog fallback record source author",
        raw_data={"category": "Fallback Category", "publisher": "Source Publisher"},
    )
    sync_state = get_sync_state()
    sync_state.remote_pages = [["stale-incomplete-record"], []]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "catalog_automation"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["phase"] == "request_creation"
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
    assert payload["automation"]["catalog"]["statusMessage"] == "Created 1 request."


@pytest.mark.django_db
def test_processing_create_requests_and_pipeline_are_backend_owned(client, monkeypatch, tmp_path):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="request-record",
        name="Request Record",
        url="https://www.example.com/books/request-record/",
        category="Fiction",
        writer="Writer One",
        translator="Translator One",
        publisher="Example Press",
    )

    sample = {
        "book_title": "Request Record",
        "author": "Writer One",
        "series": "",
        "book_type": "Fiction",
        "cover": "book_cover.jpg",
        "main_content": "<p>Request record body</p>",
        "book_info": "<p>অনুবাদ: Translator One</p>",
        "dedication": "",
        "toc": [{"title": "Chapter 1", "type": "lesson", "has_content": True}],
        "content_items": [
            {
                "title": "Chapter 1",
                "content": "<p>Request record body</p>",
                "type": "lesson",
                "parent": None,
            }
        ],
        "output_folder": str(tmp_path),
    }

    def fake_generate_exports(book_data):
        output_dir = Path(book_data["output_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text("<html><body>book</body></html>", encoding="utf-8")
        (output_dir / "Request Record.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr(
        "apps.processing.services.capture_source_page_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.services.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr("apps.processing.services.scrape_book", lambda _url: sample, raising=False)
    monkeypatch.setattr(
        "apps.processing.services.generate_exports",
        fake_generate_exports,
        raising=False,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.create_submission_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy submission flow should not be used by /api/processing")
        ),
    )

    response = client.post(
        "/api/processing/records/create-requests/",
        {"ids": [record.id]},
        content_type="application/json",
    )

    assert response.status_code == 200
    request = BookCreationRequest.objects.get(book_record=record)
    assert request.state == BookCreationRequest.State.INITIAL
    assert BookRecord.objects.get(pk=record.pk).book_creation_state == "initial"

    for _ in range(20):
        _mutation, _payload = advance_processing_pipeline(client)
        request.refresh_from_db()
        if request.state == BookCreationRequest.State.CREATED:
            break
        time_module.sleep(0.25)

    request.refresh_from_db()
    record.refresh_from_db()
    assert request.state == BookCreationRequest.State.CREATED
    assert record.book_creation_state == "created"
    assert request.submission_id is None
    assert request.linked_book is not None
    assert BookSubmission.objects.count() == 0
    assert ProcessingJob.objects.count() == 0
    created_book = Book.objects.get(pk=request.linked_book_id, deleted_at__isnull=True)
    assert created_book.title == "Request Record"
    assert created_book.raw_scraped_metadata["source_url"] == "https://www.example.com/books/request-record/"
    assert record.linked_book_id == created_book.id


def test_processing_task_requeues_if_worker_child_is_lost():
    assert kickoff_book_creation_request_task.acks_late is True
    assert kickoff_book_creation_request_task.reject_on_worker_lost is True


def test_processing_task_handles_missing_request_gracefully(monkeypatch):
    missing_request_id = "missing-processing-request"

    def raise_missing(_request_id):
        raise BookCreationRequest.DoesNotExist

    monkeypatch.setattr(
        "apps.processing.tasks.kickoff_request_processing",
        raise_missing,
    )

    result = kickoff_book_creation_request_task.run(missing_request_id)

    assert result == {
        "request_id": missing_request_id,
        "state": "deleted",
        "submission_id": "",
        "missing": True,
    }


@pytest.mark.django_db
def test_processing_sync_task_returns_json_safe_sync_snapshot(monkeypatch):
    sync_state = get_sync_state()
    remote_pages = [[record_payload("task-sync-record")], []]
    sync_state.status = ProcessingSyncStatus.PAUSED
    sync_state.progress = {
        "runMode": "catalog_automation",
        "savedData": {
            "runMode": "catalog_automation",
            "nextPageIndex": 2,
            "fetchedCount": 3,
        },
    }
    sync_state.remote_pages = remote_pages
    sync_state.page_index = 2
    sync_state.fetched_count = 3
    sync_state.skipped_count = 1
    sync_state.updated_count = 2
    sync_state.appended_count = 1
    sync_state.message = "Sync progress saved."
    sync_state.save(
        update_fields=[
            "status",
            "progress",
            "remote_pages",
            "page_index",
            "fetched_count",
            "skipped_count",
            "updated_count",
            "appended_count",
            "message",
            "updated_at",
        ]
    )

    monkeypatch.setattr(
        "apps.processing.tasks.run_processing_sync",
        lambda **_kwargs: sync_state,
    )

    result = run_processing_sync_task.run("default")

    assert result["singleton_key"] == "catalog"
    assert result["status"] == "paused"
    assert result["run_mode"] == "catalog_automation"
    assert result["page_index"] == 2
    assert result["fetched_count"] == 3
    assert result["remote_pages"] == remote_pages
    json.dumps(result)
