

@pytest.mark.django_db
def test_processing_sync_persists_records_and_reconciles_resume(client):
    login_processing_admin(client)
    BookRecord.objects.create(
        id="existing-record",
        name="Existing",
        url="https://example.test/books/existing",
        category="Old",
        writer="Writer",
        publisher="Press",
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [
                    record_payload(
                        "existing-record",
                        name="Existing Revised",
                        url="https://example.test/books/existing-revised",
                        category="Updated",
                        writer="Updated Writer",
                        translator="Updated Translator",
                        publisher="Updated Press",
                    )
                ],
                [
                    record_payload(
                        "new-record",
                        name="New Record",
                        category="Poetry",
                        writer="Remote Writer",
                        translator="Remote Translator",
                        publisher="Remote Press",
                    )
                ],
                [],
            ]
        },
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["updatedCount"] == 0
    assert BookRecord.objects.get(pk="existing-record").name == "Existing"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["updatedCount"] == 1
    existing = BookRecord.objects.get(pk="existing-record")
    assert existing.name == "Existing Revised"
    assert existing.url == "https://example.test/books/existing-revised"
    assert existing.category == "Updated"
    assert existing.writer == "Updated Writer"
    assert existing.translator == "Updated Translator"
    assert existing.publisher == "Updated Press"

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
    assert payload["sync"]["progress"]["savedData"]["nextPageIndex"] == 2
    assert payload["sync"]["updatedCount"] == 1
    assert payload["sync"]["appendedCount"] == 1
    new_record = BookRecord.objects.get(pk="new-record")
    assert new_record.name == "New Record"
    assert new_record.url == "https://example.test/books/new-record"
    assert new_record.category == "Poetry"
    assert new_record.writer == "Remote Writer"
    assert new_record.translator == "Remote Translator"
    assert new_record.publisher == "Remote Press"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/resume/",
    )
    assert payload["sync"]["status"] == "syncing"

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "idle"
    assert payload["sync"]["skippedCount"] == 0
    assert payload["sync"]["appendedCount"] == 1
    assert BookRecord.objects.filter(pk="new-record").exists()

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [
                    record_payload(
                        "existing-record",
                        name="Existing Revised",
                        url="https://example.test/books/existing-revised",
                        category="Updated",
                        writer="Updated Writer",
                        translator="Updated Translator",
                        publisher="Updated Press",
                    )
                ],
                [
                    record_payload(
                        "new-record",
                        name="New Record",
                        category="Poetry",
                        writer="Remote Writer",
                        translator="Remote Translator",
                        publisher="Remote Press",
                    )
                ],
                [],
            ]
        },
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["message"] == "Syncing catalog records."
    assert payload["sync"]["pageIndex"] == 0
    assert payload["sync"]["fetchedCount"] == 0


@pytest.mark.django_db
def test_processing_sync_mirrors_checkpoint_progress_and_clears_it_on_stop(
    client, monkeypatch
):
    login_processing_admin(client)

    class FakeCheckpointClient:
        def __init__(self):
            self.store = {}

        def set(self, key, value):
            self.store[key] = value

        def delete(self, key):
            self.store.pop(key, None)

    fake_checkpoint_client = FakeCheckpointClient()
    monkeypatch.setattr(
        "apps.processing.services.processing_checkpoint_client",
        lambda: fake_checkpoint_client,
    )

    response = client.post(
        "/api/processing/sync/start/",
        {
            "remotePages": [
                [record_payload("mirrored-sync-record", name="Mirrored Sync Record")],
                [],
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    checkpoint_key = processing_services.processing_sync_checkpoint_key("catalog")
    mirrored_payload = json.loads(fake_checkpoint_client.store[checkpoint_key])
    assert mirrored_payload["status"] == "syncing"
    assert mirrored_payload["progress"]["savedData"]["nextPageIndex"] == 0

    response = client.post("/api/processing/sync/pause/", content_type="application/json")
    assert response.status_code == 200
    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )

    mirrored_payload = json.loads(fake_checkpoint_client.store[checkpoint_key])
    assert mirrored_payload["status"] == "paused"
    assert mirrored_payload["progress"]["savedData"]["nextPageIndex"] == 1
    assert mirrored_payload["fetchedCount"] == 1

    response = client.post("/api/processing/sync/stop/", content_type="application/json")
    assert response.status_code == 200
    assert checkpoint_key not in fake_checkpoint_client.store


@pytest.mark.django_db
def test_processing_sync_uses_persisted_source_catalog_when_no_remote_pages(client):
    login_processing_admin(client)
    entry = SourceCatalogEntry.objects.create(
        source_url="https://example.test/books/source-catalog-record",
        title="Source Catalog Record",
        author_line="Source Author",
        normalized_title="source catalog record",
        normalized_display="source catalog record source author",
        raw_data={"category": "Source Category", "publisher": "Source Publisher"},
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/start/",
        {},
    )
    assert payload["sync"]["status"] == "syncing"

    payload = advance_processing_sync(client, count=2)
    assert payload["sync"]["status"] == "idle"
    record = BookRecord.objects.get(pk=str(entry.id))
    assert record.name == "Source Catalog Record"
    assert record.url == "https://example.test/books/source-catalog-record"
    assert record.category == "Source Category"
    assert record.writer == "Source Author"
    assert record.publisher == "Source Publisher"
