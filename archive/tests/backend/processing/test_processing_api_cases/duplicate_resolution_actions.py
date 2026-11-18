

@pytest.mark.django_db
def test_processing_create_again_reuses_own_linked_book_and_finishes_created(
    client,
    monkeypatch,
):
    login_processing_admin(client)
    existing_book = Book.objects.create(title="Existing Created Book", state="ready")
    record = BookRecord.objects.create(
        id="recreate-created-record",
        name="Recreate Created",
        url="https://www.example.com/books/recreate-created/",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="deleted",
        linked_book=existing_book,
    )
    processing_request = BookCreationRequest.objects.create(
        id="recreate-created-request",
        book_record=record,
        state="deleted",
        linked_book=existing_book,
    )

    monkeypatch.setattr(
        "apps.processing.services.capture_source_page_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.services.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: existing_book,
    )
    monkeypatch.setattr(
        "apps.processing.services.find_exact_existing_book",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.services.detect_metadata_duplicate",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.services.scrape_book",
        lambda *_args, **_kwargs: {
            "book_info": "",
            "main_content": "<p>body</p>",
        },
        raising=False,
    )
    monkeypatch.setattr(
        "apps.processing.services._persist_processing_book",
        lambda *_args, **_kwargs: existing_book,
    )

    response = client.post(
        "/api/processing/requests/action/",
        {"ids": [processing_request.id], "action": "create_again"},
        content_type="application/json",
    )
    assert response.status_code == 200

    for _ in range(10):
        _mutation, _payload = advance_processing_pipeline(client)
        processing_request.refresh_from_db()
        if processing_request.state == BookCreationRequest.State.CREATED:
            break
        time_module.sleep(0.1)

    processing_request.refresh_from_db()
    record.refresh_from_db()
    assert processing_request.state == "created"
    assert processing_request.linked_book_id == existing_book.id
    assert processing_request.duplicate_of_request_id is None
    assert processing_request.duplicate_of_record_id is None
    assert record.book_creation_state == "created"
    assert record.linked_book_id == existing_book.id
    assert record.is_duplicate is False
    assert record.duplicate_of_record_id is None


@pytest.mark.django_db
def test_processing_tables_repair_self_linked_duplicates_to_created(client):
    login_processing_admin(client)
    existing_book = Book.objects.create(title="Existing Ready Book", state="ready")
    record = BookRecord.objects.create(
        id="self-linked-duplicate-record",
        name="Self Linked Duplicate",
        url="https://example.test/books/self-linked-duplicate",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="duplicate",
        linked_book=existing_book,
        is_duplicate=True,
    )
    processing_request = BookCreationRequest.objects.create(
        id="self-linked-duplicate-request",
        book_record=record,
        state="duplicate",
        linked_book=existing_book,
    )
    processing_services.repair_self_linked_duplicate_requests()

    duplicate_response = client.get("/api/processing/table/?card=on-hold-duplicate")
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["pagination"]["totalCount"] == 0

    processing_request.refresh_from_db()
    record.refresh_from_db()
    assert processing_request.state == "created"
    assert processing_request.duplicate_of_request_id is None
    assert processing_request.duplicate_of_record_id is None
    assert record.book_creation_state == "created"
    assert record.is_duplicate is False
    assert record.duplicate_of_record_id is None

    created_response = client.get("/api/processing/table/?card=create-created")
    assert created_response.status_code == 200
    created_ids = {
        row["requestId"] or row["id"] for row in created_response.json()["rows"]
    }
    assert processing_request.id in created_ids


@pytest.mark.django_db
def test_duplicate_confirmation_locks_record_until_original_terminal(client):
    login_processing_admin(client)
    original_record = BookRecord.objects.create(
        id="original-record",
        name="Original",
        url="https://example.test/books/original",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="processing",
    )
    duplicate_record = BookRecord.objects.create(
        id="duplicate-record",
        name="Duplicate",
        url="https://example.test/books/duplicate",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="duplicate",
    )
    original = BookCreationRequest.objects.create(
        id="original-request",
        book_record=original_record,
        state="processing",
    )
    duplicate = BookCreationRequest.objects.create(
        id="duplicate-request",
        book_record=duplicate_record,
        state="duplicate",
        duplicate_of_request=original,
        duplicate_of_record=original_record,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/requests/action/",
        {"ids": [duplicate.id], "action": "confirm_duplicate"},
        include_lists=True,
    )
    row = next(item for item in payload["records"] if item["id"] == duplicate_record.id)
    assert row["selectable"] is False

    original.state = "failed"
    original.save(update_fields=["state", "updated_at"])
    response = client.get("/api/processing/state/")
    row = next(item for item in response.json()["records"] if item["id"] == duplicate_record.id)
    assert row["selectable"] is True


@pytest.mark.django_db
def test_duplicate_new_action_clears_duplicate_locking_and_restarts_request(client):
    login_processing_admin(client)
    existing_book = Book.objects.create(title="Existing Book", state="ready")
    original_record = BookRecord.objects.create(
        id="original-record",
        name="Original",
        url="https://example.test/books/original",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="created",
        linked_book=existing_book,
    )
    duplicate_record = BookRecord.objects.create(
        id="duplicate-record",
        name="Duplicate",
        url="https://example.test/books/duplicate",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="duplicate",
        linked_book=existing_book,
        is_duplicate=True,
        duplicate_of_record=original_record,
    )
    duplicate_request = BookCreationRequest.objects.create(
        id="duplicate-request",
        book_record=duplicate_record,
        state="duplicate",
        linked_book=existing_book,
        duplicate_of_record=original_record,
    )

    response = client.post(
        "/api/processing/requests/action/",
        {"ids": [duplicate_request.id], "action": "new"},
        content_type="application/json",
    )

    assert response.status_code == 200
    duplicate_request.refresh_from_db()
    duplicate_record.refresh_from_db()
    assert duplicate_request.state == "initial"
    assert duplicate_request.is_confirmed_not_duplicate is True
    assert duplicate_request.duplicate_confirmed is False
    assert duplicate_request.duplicate_of_request_id is None
    assert duplicate_request.duplicate_of_record_id is None
    assert duplicate_request.linked_book_id is None
    assert duplicate_record.book_creation_state == "initial"
    assert duplicate_record.linked_book_id is None
    assert duplicate_record.is_duplicate is False
    assert duplicate_record.duplicate_of_record_id is None


@pytest.mark.django_db
def test_duplicate_new_edition_action_links_existing_book_via_book_group(client):
    """Phase E: the new_edition action should ensure the existing book has a
    BookGroup and stash the group id on the submission so the to-be-created
    new book gets linked to the same group."""
    from apps.catalog.models import BookGroup
    from apps.ingestion.models import BookSubmission, SubmissionOrigin, SubmissionStatus

    login_processing_admin(client)
    existing_book = Book.objects.create(title="Existing Edition", state="ready")
    original_record = BookRecord.objects.create(
        id="original-edition-record",
        name="Original Edition",
        url="https://example.test/books/original-edition",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="created",
        linked_book=existing_book,
    )
    duplicate_record = BookRecord.objects.create(
        id="duplicate-edition-record",
        name="Duplicate Edition",
        url="https://example.test/books/duplicate-edition",
        category="Fiction",
        writer="Writer",
        publisher="Press 2",
        book_creation_state="duplicate",
        linked_book=existing_book,
        is_duplicate=True,
        duplicate_of_record=original_record,
    )
    submission = BookSubmission.objects.create(
        submitter=None,
        input_type="url",
        origin=SubmissionOrigin.AUTOMATION,
        original_input="https://example.test/books/duplicate-edition",
        normalized_input="https://example.test/books/duplicate-edition",
        resolved_url="https://example.test/books/duplicate-edition",
        status=SubmissionStatus.QUEUED,
    )
    duplicate_request = BookCreationRequest.objects.create(
        id="duplicate-edition-request",
        book_record=duplicate_record,
        state="duplicate",
        linked_book=existing_book,
        duplicate_of_record=original_record,
        submission=submission,
    )

    response = client.post(
        "/api/processing/requests/action/",
        {"ids": [duplicate_request.id], "action": "new_edition"},
        content_type="application/json",
    )
    assert response.status_code == 200

    existing_book.refresh_from_db()
    submission.refresh_from_db()
    duplicate_request.refresh_from_db()

    assert existing_book.group_id is not None
    group = BookGroup.objects.get(pk=existing_book.group_id)
    assert group.canonical_title == "Existing Edition"
    assert submission.raw_payload.get("target_book_group_id") == str(group.id)
    # Same behaviour as "new": request restarted, duplicate locking cleared.
    assert duplicate_request.state == "initial"
    assert duplicate_request.is_confirmed_not_duplicate is True
    assert duplicate_request.duplicate_of_record_id is None
