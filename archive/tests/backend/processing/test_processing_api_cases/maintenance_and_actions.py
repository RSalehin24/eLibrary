

@pytest.mark.django_db
def test_processing_state_does_not_recover_stale_processing_requests(client):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="stale-processing-record",
        name="Stale Processing Record",
        url="https://example.test/books/stale-processing-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="processing",
    )
    stale_request = BookCreationRequest.objects.create(
        id="stale-processing-request",
        book_record=record,
        state="processing",
    )
    BookCreationRequest.objects.filter(pk=stale_request.pk).update(
        updated_at=timezone.now() - timedelta(minutes=25)
    )

    response = client.get("/api/processing/state/")

    assert response.status_code == 200
    payload = response.json()
    stale_request.refresh_from_db()
    record.refresh_from_db()
    assert stale_request.state == "processing"
    assert stale_request.error_message == ""
    assert record.book_creation_state == "processing"
    row = next(item for item in payload["requests"] if item["id"] == stale_request.id)
    assert row["state"] == "processing"
    assert row["errorMessage"] == ""

    processing_services.mark_stale_processing_requests()
    stale_request.refresh_from_db()
    record.refresh_from_db()
    assert stale_request.state == "queued"
    assert record.book_creation_state == "queued"


@pytest.mark.django_db
def test_processing_maintenance_recovers_stale_processing_requests_without_browser():
    record = BookRecord.objects.create(
        id="maintenance-stale-record",
        name="Maintenance Stale Record",
        url="https://example.test/books/maintenance-stale-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="processing",
    )
    stale_request = BookCreationRequest.objects.create(
        id="maintenance-stale-request",
        book_record=record,
        state="processing",
    )
    BookCreationRequest.objects.filter(pk=stale_request.pk).update(
        updated_at=timezone.now() - timedelta(minutes=25)
    )

    result = processing_services.run_processing_maintenance()

    stale_request.refresh_from_db()
    record.refresh_from_db()
    assert result["recoveredCount"] == 1
    assert result["repairedCount"] == 0
    assert stale_request.state == "queued"
    assert record.book_creation_state == "queued"


@pytest.mark.django_db
def test_processing_table_includes_linked_book_slug_for_created_requests(client):
    login_processing_admin(client)
    linked_book = Book.objects.create(title="Linked Created Book", state="ready")
    record = BookRecord.objects.create(
        id="created-linked-record",
        name="Created Linked Record",
        url="https://example.test/books/created-linked-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="created",
        linked_book=linked_book,
    )
    BookCreationRequest.objects.create(
        id="created-linked-request",
        book_record=record,
        state="created",
        linked_book=linked_book,
    )

    response = client.get("/api/processing/table/?card=create-created")

    assert response.status_code == 200
    payload = response.json()
    assert payload["rows"][0]["linkedBookId"] == str(linked_book.id)
    assert payload["rows"][0]["linkedBookSlug"] == linked_book.slug


@pytest.mark.django_db
def test_processing_duplicate_detection_is_backend_owned(client, monkeypatch):
    login_processing_admin(client)
    existing_book = Book.objects.create(title="Existing Request Record", state="ready")
    original_record = BookRecord.objects.create(
        id="original-record",
        name="Original Request Record",
        url="https://www.example.com/books/original-request-record/",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="created",
        linked_book=existing_book,
    )
    original_request = BookCreationRequest.objects.create(
        id="original-request",
        book_record=original_record,
        state="created",
        linked_book=existing_book,
    )
    duplicate_record = BookRecord.objects.create(
        id="duplicate-record",
        name="Duplicate Request Record",
        url="https://www.example.com/books/duplicate-request-record/",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
    )

    monkeypatch.setattr(
        "apps.processing.services.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: existing_book,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.create_submission_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy submission flow should not be used by duplicate detection")
        ),
    )

    response = client.post(
        "/api/processing/records/create-requests/",
        {"ids": [duplicate_record.id]},
        content_type="application/json",
    )
    assert response.status_code == 200
    duplicate_request = BookCreationRequest.objects.get(book_record=duplicate_record)

    for _ in range(10):
        _mutation, _payload = advance_processing_pipeline(client)
        duplicate_request.refresh_from_db()
        if duplicate_request.state == BookCreationRequest.State.DUPLICATE:
            break
        time_module.sleep(0.1)

    duplicate_request.refresh_from_db()
    duplicate_record.refresh_from_db()
    assert duplicate_request.state == "duplicate"
    assert duplicate_request.submission_id is None
    assert duplicate_request.duplicate_of_request_id == original_request.id
    assert duplicate_request.duplicate_of_record_id == original_record.id
    assert duplicate_record.book_creation_state == "duplicate"
    assert BookSubmission.objects.count() == 0
    assert ProcessingJob.objects.count() == 0


@pytest.mark.django_db
def test_processing_actions_persist_request_state_and_book_deletion(client):
    login_processing_admin(client)
    created_book = Book.objects.create(title="Created Book", state="ready")
    paused_record = BookRecord.objects.create(
        id="paused-record",
        name="Paused",
        url="https://example.test/books/paused",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="paused",
    )
    failed_record = BookRecord.objects.create(
        id="failed-record",
        name="Failed",
        url="https://example.test/books/failed",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="failed",
    )
    created_record = BookRecord.objects.create(
        id="created-record",
        name="Created",
        url="https://example.test/books/created",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="created",
        linked_book=created_book,
    )
    paused = BookCreationRequest.objects.create(
        id="paused-request",
        book_record=paused_record,
        state="paused",
        progress={"checkpoint": "chapter-4", "savedAt": timezone.now().isoformat(), "savedData": {}},
    )
    failed = BookCreationRequest.objects.create(
        id="failed-request",
        book_record=failed_record,
        state="failed",
        error_message="Retry threshold exceeded",
    )
    created = BookCreationRequest.objects.create(
        id="created-request",
        book_record=created_record,
        state="created",
        linked_book=created_book,
    )

    response = client.post(
        "/api/processing/requests/action/",
        {"ids": [paused.id], "action": "resume"},
        content_type="application/json",
    )
    assert response.status_code == 200
    paused.refresh_from_db()
    assert paused.state == "initial"
    assert paused.is_resumed is True

    response = client.post(
        "/api/processing/requests/action/",
        {"ids": [failed.id], "action": "retry"},
        content_type="application/json",
    )
    assert response.status_code == 200
    failed.refresh_from_db()
    assert failed.state == "initial"
    assert failed.error_message == ""

    response = client.post(
        "/api/processing/requests/action/",
        {"ids": [created.id], "action": "delete", "deleteBook": True},
        content_type="application/json",
    )
    assert response.status_code == 200
    created.refresh_from_db()
    created_book.refresh_from_db()
    assert created.state == "deleted"
    assert created_book.deleted_at is not None
