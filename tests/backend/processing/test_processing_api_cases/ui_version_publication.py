

@pytest.mark.django_db
def test_save_sync_state_refreshes_catalog_automation_projection_without_bumping_its_domain(
    django_capture_on_commit_callbacks,
):
    state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    previous_versions = processing_services.processing_ui_versions_map(
        domains=["catalog-sync", "catalog-automation"]
    )

    state.status = ProcessingSyncStatus.SYNCING
    state.message = "Catalog sync is running."
    with django_capture_on_commit_callbacks(execute=True):
        processing_services.save_sync_state(state)

    current_versions = processing_services.processing_ui_versions_map(
        domains=["catalog-sync", "catalog-automation"]
    )
    catalog_automation_projection = processing_services.processing_ui_shared_projection_payload(
        "catalog-automation"
    )

    assert current_versions["catalog-sync"] == previous_versions["catalog-sync"] + 1
    assert current_versions["catalog-automation"] == previous_versions["catalog-automation"]
    assert catalog_automation_projection["sync"]["status"] == "syncing"
    assert catalog_automation_projection["sync"]["message"] == "Catalog sync is running."


@pytest.mark.django_db
def test_collect_processing_ui_version_updates_tracks_committed_versions(
    django_capture_on_commit_callbacks,
):
    state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    previous_versions = processing_services.processing_ui_versions_map(
        domains=["catalog-sync"]
    )

    state.status = ProcessingSyncStatus.SYNCING
    state.message = "Catalog sync is running."
    with processing_services.collect_processing_ui_version_updates() as versions:
        with django_capture_on_commit_callbacks(execute=True):
            processing_services.save_sync_state(state)

    assert versions == {
        "catalog-sync": previous_versions["catalog-sync"] + 1,
    }


@pytest.mark.django_db
def test_save_sync_state_incomplete_publishes_only_incomplete_automation_domain(
    django_capture_on_commit_callbacks,
):
    state = get_sync_state(PROCESSING_SYNC_KEY_INCOMPLETE)
    previous_versions = processing_services.processing_ui_versions_map(
        domains=["incomplete-automation", "catalog-sync"]
    )

    state.status = ProcessingSyncStatus.SYNCING
    state.message = "Incomplete sync is running."
    with django_capture_on_commit_callbacks(execute=True):
        processing_services.save_sync_state(state)

    current_versions = processing_services.processing_ui_versions_map(
        domains=["incomplete-automation", "catalog-sync"]
    )
    assert (
        current_versions["incomplete-automation"]
        == previous_versions["incomplete-automation"] + 1
    )
    assert current_versions["catalog-sync"] == previous_versions["catalog-sync"]


@pytest.mark.django_db
def test_processing_request_action_response_excludes_unrelated_version_bumps(
    client,
    monkeypatch,
):
    login_processing_admin(client)
    record = BookRecord.objects.create(
        id="mutation-scope-record",
        name="Mutation Scope Record",
        url="https://example.test/books/mutation-scope-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="initial",
    )
    processing_request = BookCreationRequest.objects.create(
        id="mutation-scope-request",
        book_record=record,
        state="initial",
    )
    rebuild_processing_ui_state()

    real_apply_request_action = processing_services.apply_request_action

    def apply_action_with_unrelated_bump(*args, **kwargs):
        changed = real_apply_request_action(*args, **kwargs)
        version_row = processing_services.ProcessingUiDomainVersion.objects.get(
            domain="catalog-sync"
        )
        version_row.version += 1
        version_row.save(update_fields=["version", "updated_at"])
        return changed

    monkeypatch.setattr(
        "apps.processing.views.apply_request_action",
        apply_action_with_unrelated_bump,
    )

    response = client.post(
        "/api/processing/requests/action/",
        {
            "ids": [processing_request.id],
            "action": "delete",
            "deleteBook": False,
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["versions"]
    assert "catalog-sync" not in payload["versions"]


@pytest.mark.django_db
def test_catalog_record_upsert_bumps_only_catalog_domains(
    django_capture_on_commit_callbacks,
):
    record = BookRecord.objects.create(
        id="catalog-upsert-record",
        name="Catalog Upsert Record",
        url="https://example.test/books/catalog-upsert-record",
        category="Fiction",
        writer="Writer One",
        publisher="Example Press",
        book_creation_state="initial",
    )
    BookCreationRequest.objects.create(
        id="catalog-upsert-request",
        book_record=record,
        state="initial",
    )
    rebuild_processing_ui_state()
    previous_versions = processing_services.processing_ui_versions_map(
        domains=["catalog-overview", "catalog-records", "create-requests"]
    )

    with django_capture_on_commit_callbacks(execute=True):
        processing_services.upsert_remote_records(
            [
                record_payload(
                    "catalog-upsert-record",
                    name="Catalog Upsert Record Revised",
                    category="History",
                )
            ]
        )

    current_versions = processing_services.processing_ui_versions_map(
        domains=["catalog-overview", "catalog-records", "create-requests"]
    )
    assert (
        current_versions["catalog-overview"]
        == previous_versions["catalog-overview"] + 1
    )
    assert (
        current_versions["catalog-records"]
        == previous_versions["catalog-records"] + 1
    )
    assert current_versions["create-requests"] == previous_versions["create-requests"]


@pytest.mark.django_db
def test_processing_state_returns_weekly_automation_defaults_without_placeholder(client):
    login_processing_admin(client)

    response = client.get("/api/processing/state/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["automation"]["catalog"]["interval"] == "weekly"
    assert payload["automation"]["catalog"]["time"] == "03:00"
    assert payload["automation"]["catalog"]["statusMessage"] == ""
    assert payload["automation"]["incomplete"]["interval"] == "weekly"
    assert payload["automation"]["incomplete"]["time"] == "03:00"
    assert payload["automation"]["incomplete"]["statusMessage"] == ""


@pytest.mark.django_db
def test_processing_state_exposes_decoded_bangla_display_urls(client):
    login_processing_admin(client)
    encoded_url = (
        "https://www.example.com/books/"
        "%E0%A6%85%E0%A6%97%E0%A7%8D%E0%A6%A8%E0%A6%BF%E0%A6%AA%E0%A6%B0"
        "%E0%A7%80%E0%A6%95%E0%A7%8D%E0%A6%B7%E0%A6%BE-%E0%A6%86%E0%A6%B6"
        "%E0%A6%BE%E0%A6%AA%E0%A7%82%E0%A6%B0%E0%A7%8D%E0%A6%A3%E0%A6%BE/"
    )
    record = BookRecord.objects.create(
        id="bangla-link-record",
        name="অগ্নিপরীক্ষা",
        url=encoded_url,
        category="উপন্যাস",
        writer="আশাপূর্ণা দেবী",
        publisher="বাংলা লাইব্রেরি",
    )

    response = client.get("/api/processing/state/")

    assert response.status_code == 200
    payload = response.json()
    entry = next(item for item in payload["records"] if item["id"] == record.id)
    assert entry["url"] == encoded_url
    assert (
        entry["displayUrl"]
        == "https://www.example.com/books/অগ্নিপরীক্ষা-আশাপূর্ণা/"
    )
    assert entry["displayPath"] == "books/অগ্নিপরীক্ষা-আশাপূর্ণা"
