

@pytest.mark.django_db
def test_automation_and_incomplete_resolution_are_persisted(client):
    login_processing_admin(client)
    BookRecord.objects.create(
        id="auto-new",
        name="Auto New",
        url="https://example.test/books/auto-new",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="not_created",
    )
    BookRecord.objects.create(
        id="auto-created",
        name="Auto Created",
        url="https://example.test/books/auto-created",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="created",
    )
    incomplete = BookRecord.objects.create(
        id="incomplete-record",
        name="Incomplete Record",
        url="https://example.test/books/incomplete-record",
        category="অসম্পূর্ণ বই",
        writer="Writer",
        publisher="Press",
        was_incomplete=True,
        will_resolve_to_category="Novel",
    )

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/",
        {"enabled": True, "interval": "weekly", "time": "04:30"},
    )
    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/catalog/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "catalog_automation"

    response = advance_processing_sync(client, count=2)
    assert BookCreationRequest.objects.filter(book_record_id="auto-new", state="initial").exists()
    assert not BookCreationRequest.objects.filter(book_record_id="auto-created", state="initial").exists()

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/automation/incomplete/",
        {"enabled": True, "interval": "daily", "time": "03:00"},
    )
    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/incomplete/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "incomplete_automation"

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    incomplete.refresh_from_db()
    assert incomplete.category == "Novel"
    assert incomplete.resolved_from_incomplete is True
    assert BookCreationRequest.objects.filter(
        book_record=incomplete,
        state="created",
    ).exists()
