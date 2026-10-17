from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_discovery.commands import request_source_discovery
from apps.ingestion.source_discovery.configuration import discovery_configuration
from apps.processing.job_models import BackgroundJob
from django.utils import timezone
from rest_framework.test import APIClient
from test_source_discovery import archive_html, controlled_replies, execute

pytestmark = pytest.mark.django_db


@pytest.fixture
def unfinished_job(settings, tmp_path):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_CATALOG_URL = "https://source.test/books/"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    settings.RUNTIME_STORAGE_DIR = tmp_path
    actor = User.objects.create_user(
        email="unfinished-catalog@example.test", is_staff=True
    )
    configuration = discovery_configuration("unfinished")
    return request_source_discovery(
        actor,
        {
            "operation_id": uuid4(),
            "catalog_scope": "unfinished",
            "max_pages": 2,
            "configuration_revision": configuration["configuration_revision"],
        },
    )


def entry(url, raw):
    return SourceCatalogEntry.objects.create(
        source_url=f"https://source.test/books/{url}/",
        title=url,
        normalized_title=url,
        normalized_display=url,
        raw_data=raw,
    )


def test_unfinished_scan_uses_the_source_category_and_preserves_other_metadata(
    unfinished_job, monkeypatch
):
    source = entry("story-1", {"manual_note": "kept"})
    before = source.updated_at
    adapter = controlled_replies(monkeypatch, [(200, {}, archive_html(1))])
    execute(unfinished_job)
    assert unfinished_job.state == "succeeded"
    assert "/genres/" in adapter.calls[0][0].url
    source.refresh_from_db()
    assert source.raw_data["source_unfinished"] is True
    assert source.raw_data["manual_note"] == "kept" and source.updated_at > before
    client = APIClient()
    client.force_authenticate(unfinished_job.requested_by)
    response = client.get("/api/v1/manage/sources/", {"catalog_scope": "unfinished"})
    assert [item["id"] for item in response.json()["entries"]] == [str(source.pk)]


def test_processing_failures_are_not_the_websites_unfinished_category(unfinished_job):
    source = entry("broken-export", {})
    BackgroundJob.objects.create(
        kind="process_source",
        state="failed",
        source_record=source,
        error_code="source_exports_missing",
        available_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(unfinished_job.requested_by)
    response = client.get("/api/v1/manage/sources/", {"catalog_scope": "unfinished"})
    assert response.status_code == 200 and response.json()["entries"] == []


def test_a_complete_scan_resolves_books_removed_from_the_source_unfinished_category(
    unfinished_job, monkeypatch
):
    stale = entry(
        "finished-story", {"source_unfinished": True, "unfinished_scan": str(uuid4())}
    )
    controlled_replies(monkeypatch, [(200, {}, archive_html(1))])
    execute(unfinished_job)
    stale.refresh_from_db()
    assert stale.raw_data["source_unfinished"] is False


def test_a_bounded_scan_does_not_mark_unvisited_unfinished_books_complete(
    unfinished_job, monkeypatch
):
    stale = entry(
        "still-unfinished", {"source_unfinished": True, "unfinished_scan": str(uuid4())}
    )
    unfinished_job.input["command"]["max_pages"] = 1
    unfinished_job.save()
    controlled_replies(
        monkeypatch,
        [(200, {}, archive_html(1, "https://source.test/genres/unfinished/page/2/"))],
    )
    execute(unfinished_job)
    stale.refresh_from_db()
    assert unfinished_job.checkpoint["more_pages_available"]
    assert stale.raw_data["source_unfinished"] is True


def test_an_empty_recognized_unfinished_archive_is_a_valid_complete_scan(
    unfinished_job, monkeypatch
):
    stale = entry(
        "finished-story", {"source_unfinished": True, "unfinished_scan": str(uuid4())}
    )
    controlled_replies(
        monkeypatch, [(200, {}, b'<div class="facetwp-template"></div>')]
    )
    execute(unfinished_job)
    stale.refresh_from_db()
    assert unfinished_job.state == "succeeded"
    assert stale.raw_data["source_unfinished"] is False
