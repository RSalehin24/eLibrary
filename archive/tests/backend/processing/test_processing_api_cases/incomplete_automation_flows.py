

@pytest.mark.django_db
def test_incomplete_automation_can_pause_resume_and_complete(client):
    login_processing_admin(client)
    BookRecord.objects.create(
        id="resume-incomplete-a",
        name="Resume Incomplete A",
        url="https://example.test/books/resume-incomplete-a",
        category="অসম্পূর্ণ বই",
        writer="Writer One",
        publisher="Example Press",
        was_incomplete=True,
        resolved_from_incomplete=False,
        will_resolve_to_category="Novel",
    )
    BookRecord.objects.create(
        id="resume-incomplete-b",
        name="Resume Incomplete B",
        url="https://example.test/books/resume-incomplete-b",
        category="অসম্পূর্ণ বই",
        writer="Writer Two",
        publisher="Example Press",
        was_incomplete=True,
        resolved_from_incomplete=False,
        will_resolve_to_category="Novel",
    )

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/automation/incomplete/run/",
    )
    sync_state = get_sync_state(PROCESSING_SYNC_KEY_INCOMPLETE)
    sync_state.remote_pages = [["resume-incomplete-a"], ["resume-incomplete-b"], []]
    sync_state.save(update_fields=["remote_pages", "updated_at"])

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
    assert payload["sync"]["runMode"] == "incomplete_automation"
    assert BookRecord.objects.get(pk="resume-incomplete-a").resolved_from_incomplete is True
    assert BookRecord.objects.get(pk="resume-incomplete-b").resolved_from_incomplete is False

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/resume/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "incomplete_automation"
    assert payload["sync"]["message"] == "Restarting incomplete catalog sync from the beginning."

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "idle"
    assert payload["sync"]["message"] == "Incomplete catalog sync complete. Updated 2 books."
    assert BookRecord.objects.get(pk="resume-incomplete-b").resolved_from_incomplete is True


@pytest.mark.django_db
def test_incomplete_automation_uses_incomplete_sync_remote_pages_source(client, monkeypatch):
    login_processing_admin(client)
    expected_pages = [
        [
            {
                "id": "live-incomplete-record",
                "name": "Live Incomplete Record",
                "url": "https://www.example.com/books/live-incomplete-record/",
                "category": "অসম্পূর্ণ বই",
                "writer": "Live Writer",
                "translator": "",
                "composer": "",
                "publisher": "Live Press",
                "updatedAt": timezone.now().isoformat(),
                "wasIncomplete": True,
                "willResolveToCategory": "Novel",
            }
        ],
        [],
    ]
    monkeypatch.setattr(
        "apps.processing.services.incomplete_sync_remote_pages",
        lambda: expected_pages,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/incomplete/run/",
    )
    sync_state = get_sync_state(PROCESSING_SYNC_KEY_INCOMPLETE)
    assert sync_state.remote_pages == expected_pages
    assert payload["sync"]["runMode"] == "incomplete_automation"


@pytest.mark.django_db
def test_incomplete_automation_live_sync_fetches_incrementally_and_resolves_stale_records(
    client,
    monkeypatch,
):
    login_processing_admin(client)
    BookRecord.objects.create(
        id="stale-incomplete-live",
        name="Stale Incomplete Live",
        url="https://www.example.com/books/stale-incomplete-live/",
        category="অসম্পূর্ণ বই",
        writer="Writer One",
        publisher="Example Press",
        was_incomplete=True,
        resolved_from_incomplete=False,
        will_resolve_to_category="Novel",
    )

    page_calls = []

    def fake_fetch_live_incomplete_page(_resolver, page_number):
        page_calls.append(page_number)
        if page_number == 1:
            return [
                {
                    "id": "live-incomplete-page-1",
                    "name": "Live Incomplete Page 1",
                    "url": "https://www.example.com/books/live-incomplete-page-1/",
                    "category": "অসম্পূর্ণ বই",
                    "writer": "Live Writer",
                    "translator": "",
                    "composer": "",
                    "publisher": "Live Press",
                    "updatedAt": timezone.now().isoformat(),
                    "wasIncomplete": True,
                    "resolvedFromIncomplete": False,
                    "willResolveToCategory": "Novel",
                }
            ]
        return []

    monkeypatch.setattr(
        "apps.processing.services.should_use_live_incomplete_fetch",
        lambda: True,
    )
    monkeypatch.setattr(
        "apps.processing.services.fetch_live_incomplete_page",
        fake_fetch_live_incomplete_page,
    )

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/automation/incomplete/run/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["runMode"] == "incomplete_automation"
    assert "remotePages" not in payload["sync"]
    assert payload["sync"]["progress"]["savedData"]["liveFetch"] is True

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["fetchedCount"] == 1
    assert BookRecord.objects.filter(pk="live-incomplete-page-1").exists()

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/advance/",
    )
    assert payload["sync"]["status"] == "idle"
    assert payload["sync"]["message"] == "Incomplete catalog sync complete. Updated 1 book."
    assert page_calls == [1, 2]
    stale_record = BookRecord.objects.get(pk="stale-incomplete-live")
    assert stale_record.resolved_from_incomplete is True
    assert stale_record.category == "Novel"


@pytest.mark.django_db
def test_incomplete_automation_live_sync_pause_and_resume_restarts_from_beginning(
    client,
    monkeypatch,
):
    login_processing_admin(client)

    def fake_fetch_live_incomplete_page(_resolver, page_number):
        if page_number == 1:
            return [
                {
                    "id": "paused-live-incomplete",
                    "name": "Paused Live Incomplete",
                    "url": "https://www.example.com/books/paused-live-incomplete/",
                    "category": "অসম্পূর্ণ বই",
                    "writer": "Live Writer",
                    "translator": "",
                    "composer": "",
                    "publisher": "Live Press",
                    "updatedAt": timezone.now().isoformat(),
                    "wasIncomplete": True,
                    "resolvedFromIncomplete": False,
                    "willResolveToCategory": "Novel",
                }
            ]
        return []

    monkeypatch.setattr(
        "apps.processing.services.should_use_live_incomplete_fetch",
        lambda: True,
    )
    monkeypatch.setattr(
        "apps.processing.services.fetch_live_incomplete_page",
        fake_fetch_live_incomplete_page,
    )

    _mutation, _payload = post_processing_mutation(
        client,
        "/api/processing/automation/incomplete/run/",
    )

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
    assert payload["sync"]["progress"]["savedData"]["liveFetch"] is True
    assert payload["sync"]["progress"]["savedData"]["nextPageIndex"] == 1

    sync_state = get_sync_state(PROCESSING_SYNC_KEY_INCOMPLETE)
    assert sync_state.page_index == 1
    assert len(sync_state.remote_pages) == 1

    _mutation, payload = post_processing_mutation(
        client,
        "/api/processing/sync/resume/",
    )
    assert payload["sync"]["status"] == "syncing"
    assert payload["sync"]["message"] == "Restarting incomplete catalog sync from the beginning."
    assert payload["sync"]["progress"]["savedData"]["liveFetch"] is True
    assert payload["sync"]["progress"]["savedData"]["nextPageIndex"] == 0

    sync_state.refresh_from_db()
    assert sync_state.page_index == 0
    assert sync_state.remote_pages == []
