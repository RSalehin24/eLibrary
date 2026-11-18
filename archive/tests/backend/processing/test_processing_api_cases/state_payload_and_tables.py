

@pytest.mark.django_db
def test_processing_state_normalizes_legacy_automation_defaults(client):
    login_processing_admin(client)
    catalog = ProcessingAutomationSettings.objects.get(
        kind=ProcessingAutomationKind.CATALOG
    )
    catalog.interval = "daily"
    catalog.time = time(2, 0)
    catalog.saved = False
    catalog.status_message = "Not configured."
    catalog.save(
        update_fields=["interval", "time", "saved", "status_message", "updated_at"]
    )
    incomplete = ProcessingAutomationSettings.objects.get(
        kind=ProcessingAutomationKind.INCOMPLETE
    )
    incomplete.interval = "daily"
    incomplete.time = time(3, 0)
    incomplete.saved = False
    incomplete.status_message = "Not configured."
    incomplete.save(
        update_fields=["interval", "time", "saved", "status_message", "updated_at"]
    )
    rebuild_processing_ui_state()

    response = client.get("/api/processing/state/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["automation"]["catalog"]["interval"] == "weekly"
    assert payload["automation"]["catalog"]["time"] == "03:00"
    assert payload["automation"]["catalog"]["statusMessage"] == ""
    assert payload["automation"]["incomplete"]["interval"] == "weekly"
    assert payload["automation"]["incomplete"]["time"] == "03:00"
    assert payload["automation"]["incomplete"]["statusMessage"] == ""

    catalog.refresh_from_db()
    incomplete.refresh_from_db()
    assert catalog.interval == "daily"
    assert catalog.time == time(2, 0)
    assert catalog.status_message == "Not configured."
    assert incomplete.interval == "daily"
    assert incomplete.time == time(3, 0)
    assert incomplete.status_message == "Not configured."


@pytest.mark.django_db
def test_processing_state_supports_summary_only_payload(client):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="summary-only-record",
        name="Summary Only",
        url="https://example.test/books/summary-only",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="not_created",
        was_incomplete=True,
    )
    BookCreationRequest.objects.create(
        id="summary-only-request",
        book_record=record,
        state="failed",
        error_message="Pipeline failed after retries.",
    )
    rebuild_processing_ui_state()

    response = client.get("/api/processing/state/?includeLists=0")

    assert response.status_code == 200
    payload = response.json()
    assert "records" not in payload
    assert "requests" not in payload
    assert "versions" in payload
    assert payload["summary"]["catalog"]["records"] == 1
    assert payload["summary"]["catalog"]["onHold"] == 1
    assert payload["summary"]["onHold"]["failed"] == 1
    assert payload["summary"]["incomplete"]["incomplete"] == 1
    assert (
        payload["summary"]["notifications"]["latestFailedMessage"]
        == "Pipeline failed after retries."
    )
    assert payload["cards"]["catalog-overview"]["card"] == "catalog-overview"
    assert payload["cards"]["create-overview"]["card"] == "create-overview"
    assert payload["cards"]["catalog-sync"]["card"] == "catalog-sync"


@pytest.mark.django_db
def test_processing_table_paginates_catalog_rows_and_applies_filters(client):
    login_processing_admin(client)

    created_ids = set()
    for index in range(75):
        record = BookRecord.objects.create(
            id=f"table-record-{index:02d}",
            name=f"Table Record {index:02d}",
            url=f"https://example.test/books/table-record-{index:02d}",
            category="Poetry" if index % 2 == 0 else "Novel",
            writer="Writer",
            publisher="Press",
            book_creation_state="not_created",
        )
        if index < 6:
            BookCreationRequest.objects.create(
                id=f"table-request-{index:02d}",
                book_record=record,
                state="created",
            )
            created_ids.add(record.id)

    response = client.get("/api/processing/table/?card=catalog-records&limit=60")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["rows"]) == 60
    assert payload["pagination"]["totalCount"] == 75
    assert payload["pagination"]["hasMore"] is True
    assert payload["hasMore"] is True
    assert payload["pagination"]["nextOffset"] == 60
    assert "Novel" in payload["filters"]["categoryOptions"]
    assert "Poetry" in payload["filters"]["categoryOptions"]
    assert "created" in payload["filters"]["statusOptions"]
    assert "not_created" in payload["filters"]["statusOptions"]
    assert {row["status"] for row in payload["rows"]} == {"not_created"}

    response = client.get("/api/processing/table/?card=catalog-records&offset=60&limit=60")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["rows"]) == 15
    assert payload["pagination"]["hasMore"] is False
    assert payload["hasMore"] is False
    assert [row["status"] for row in payload["rows"][:9]] == ["not_created"] * 9
    assert [row["status"] for row in payload["rows"][9:]] == ["created"] * 6

    response = client.get(
        "/api/processing/table/?card=catalog-records&category=Poetry&status=created"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["totalCount"] == 3
    assert {row["recordId"] for row in payload["rows"]} == {
        record_id for record_id in created_ids if record_id.endswith(("00", "02", "04"))
    }
    assert all(row["category"] == "Poetry" for row in payload["rows"])
    assert all(row["status"] == "created" for row in payload["rows"])


@pytest.mark.django_db
def test_processing_table_keeps_create_cards_scoped_to_request_status(client):
    login_processing_admin(client)

    card_states = {
        "create-requests": "initial",
        "create-queue": "queued",
        "create-processing": "processing",
        "create-created": "created",
    }
    request_ids = {}

    for card_id, status in card_states.items():
        record = BookRecord.objects.create(
            id=f"{card_id}-record",
            name=f"{card_id} title",
            url=f"https://example.test/books/{card_id}",
            category="Reference",
            writer="Writer One",
            publisher="Example Press",
            book_creation_state=status,
        )
        request = BookCreationRequest.objects.create(
            id=f"{card_id}-request",
            book_record=record,
            state=status,
        )
        request_ids[card_id] = str(request.id)

    for card_id, status in card_states.items():
        response = client.get(f"/api/processing/table/?card={card_id}")

        assert response.status_code == 200
        payload = response.json()
        assert [row["requestId"] for row in payload["rows"]] == [request_ids[card_id]]
        assert {row["status"] for row in payload["rows"]} == {status}
        assert payload["filters"]["statusOptions"] == [status]


@pytest.mark.django_db
def test_upsert_remote_records_recovers_when_concurrent_insert_wins(monkeypatch):
    payload = record_payload(
        "race-record",
        name="Race Winner",
        url="https://example.test/books/race-record",
        category="Novel",
        writer="Writer One",
        publisher="Example Press",
    )
    original_create = BookRecord.objects.create
    race_triggered = {"value": False}

    def create_with_concurrent_insert(**kwargs):
        if race_triggered["value"]:
            return original_create(**kwargs)

        race_triggered["value"] = True
        original_create(
            id="race-record-competing",
            name="Competing Insert",
            url=kwargs["url"],
            category="Poetry",
            writer="Other Writer",
            publisher="Other Press",
        )
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr(BookRecord.objects, "create", create_with_concurrent_insert)

    result = processing_services.upsert_remote_records([payload])

    record = BookRecord.objects.get(url=payload["url"])
    assert BookRecord.objects.count() == 1
    assert result["appended_count"] == 0
    assert result["updated_count"] == 1
    assert result["skipped_count"] == 0
    assert record.name == "Race Winner"
    assert record.category == "Novel"
    assert record.writer == "Writer One"
    assert record.publisher == "Example Press"
