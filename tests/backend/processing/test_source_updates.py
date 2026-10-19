from contextlib import nullcontext
from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, BookSource
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_discovery.commands import request_source_discovery
from apps.ingestion.source_discovery.configuration import discovery_configuration
from apps.ingestion.source_discovery.updates import (
    save_published_probe,
    save_update_probe,
)
from apps.ingestion.source_processing.transport import ControlledSourceSession
from apps.ingestion.source_workspace.update_probe import source_update_probe
from apps.processing.jobs.worker import run_background_job
from bs4 import BeautifulSoup
from django.utils import timezone
from source_transport_fixture import FixtureAdapter, fixture_request_slot

pytestmark = pytest.mark.django_db
URL = "https://source.test/books/story/"


def test_completed_source_books_remain_visible_until_the_updated_edition_is_published(
    client, settings
):
    settings.SOURCE_SITE_HOST = "source.test"
    actor = User.objects.create_user(
        email="source-completed@library.test", is_staff=True
    )
    book = Book.objects.create(title="Completed", state="published")
    entry = SourceCatalogEntry.objects.create(
        source_url=URL,
        title="Completed",
        catalog_book=book,
        raw_data={
            "source_unfinished": False,
            "source_was_unfinished": True,
            "source_finished_at": timezone.now().isoformat(),
        },
    )
    probe = source_update_probe(BeautifulSoup(page(), "html.parser"), URL)
    revision = entry.updated_at
    save_update_probe(entry, probe, probe)
    client.force_login(actor)
    result = client.get(
        "/api/v1/manage/sources/?catalog_scope=unfinished&status=updated"
    ).json()
    assert result["entries"][0]["source_update"]["source_complete"]
    save_published_probe(entry, probe)
    assert (
        client.get("/api/v1/manage/sources/?catalog_scope=unfinished").json()["entries"]
        == []
    )
    entry.refresh_from_db()
    assert entry.updated_at == revision


def page(chapters=1, nonce="public"):
    links = "".join(
        f'<a href="/lessons/chapter-{index}/">Chapter {index}</a>'
        for index in range(chapters)
    )
    return f'<div class="entry-content"><p>Source introduction.</p>{links}<div data-pager-nonce="{nonce}"></div></div>'


def test_update_probe_ignores_pager_nonce_but_detects_new_chapters(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    first = source_update_probe(BeautifulSoup(page(), "html.parser"), URL)
    repeat = source_update_probe(
        BeautifulSoup(page(nonce="changed"), "html.parser"), URL
    )
    changed = source_update_probe(BeautifulSoup(page(chapters=2), "html.parser"), URL)
    assert first == repeat
    assert first["signature"] != changed["signature"]
    assert first["chapter_count"] == 1 and changed["chapter_count"] == 2


def test_updates_filter_and_evidence_do_not_invalidate_source_revisions(
    client, settings
):
    settings.SOURCE_SITE_HOST = "source.test"
    actor = User.objects.create_user(email="source-update@library.test", is_staff=True)
    book = Book.objects.create(title="Book", state="published")
    entry = SourceCatalogEntry.objects.create(
        source_url=URL,
        title="Book",
        catalog_book=book,
        raw_data={"source_unfinished": True},
    )
    BookSource.objects.create(book=book, source_url=URL, normalized_source_url=URL)
    revision = entry.updated_at
    baseline = source_update_probe(BeautifulSoup(page(), "html.parser"), URL)
    changed = source_update_probe(BeautifulSoup(page(chapters=2), "html.parser"), URL)
    save_update_probe(entry, changed, baseline)
    entry.refresh_from_db()
    assert entry.updated_at == revision and entry.raw_data["source_unfinished"]
    client.force_login(actor)
    response = client.get(
        "/api/v1/manage/sources/?catalog_scope=unfinished&status=updated"
    )
    assert (
        response.status_code == 200
        and response.json()["pagination"]["total_count"] == 1
    )
    update = response.json()["entries"][0]["source_update"]
    assert update["status"] == "available" and update["chapter_count"] == 2
    assert update["published_chapter_count"] == 1 and update["checked_at"]
    save_update_probe(entry, changed, changed)
    assert client.get("/api/v1/manage/sources/?status=updated").json()["entries"] == []


def test_catalog_refresh_checks_published_unfinished_books_automatically(
    settings, tmp_path, monkeypatch
):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_CATALOG_URL = "https://source.test/books/"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    settings.RUNTIME_STORAGE_DIR = tmp_path
    actor = User.objects.create_user(
        email="source-update-scan@library.test", is_staff=True
    )
    book = Book.objects.create(title="Book", state="published")
    baseline = source_update_probe(BeautifulSoup(page(), "html.parser"), URL)
    entry = SourceCatalogEntry.objects.create(
        source_url=URL,
        title="Book",
        normalized_title="book",
        normalized_display="book",
        catalog_book=book,
        raw_data={
            "source_unfinished": True,
            "source_update": {
                "published_signature": baseline["signature"],
                "published_chapter_count": 1,
            },
        },
    )
    adapter = FixtureAdapter(
        [
            (200, {}, f'<article><h2><a href="{URL}">Book</a></h2></article>'.encode()),
            (200, {}, page(chapters=2).encode()),
        ]
    )

    def session(boundary):
        result = ControlledSourceSession(boundary, fixture_request_slot)
        result.mount("https://", adapter)
        return result

    monkeypatch.setattr(
        "apps.ingestion.source_discovery.worker.ControlledSourceSession", session
    )
    monkeypatch.setattr(
        "apps.ingestion.source_discovery.updates.ControlledSourceSession", session
    )
    job = request_source_discovery(
        actor,
        {
            "operation_id": uuid4(),
            "max_pages": 1,
            "configuration_revision": discovery_configuration()[
                "configuration_revision"
            ],
        },
    )
    run_background_job(job.dispatches.get().pk, lambda _: nullcontext())
    job.refresh_from_db()
    entry.refresh_from_db()
    assert job.state == "succeeded" and len(adapter.calls) == 2
    assert entry.raw_data["source_update"]["status"] == "available"
    assert job.checkpoint["update_checks"] == [str(entry.pk)]


def test_changed_unfinished_book_queues_one_staged_edition_when_automation_enables_rebuilding(
    source_job,
):
    from datetime import timedelta
    from types import SimpleNamespace

    from apps.catalog.models import BookSource
    from apps.ingestion.source_discovery.rebuilding import rebuild_updated_source
    from apps.processing.automation_models import AutomationRun, SourceAutomation
    from django.utils import timezone

    book = Book.objects.create(title="Unfinished edition", state="published")
    entry = source_job.source_record
    entry.catalog_book = book
    entry.raw_data = {
        "source_update": {"status": "available", "signature": "new-chapters"}
    }
    entry.save()
    BookSource.objects.create(
        book=book, source_url=entry.source_url, normalized_source_url=entry.source_url
    )
    source_job.state = "cancelled"
    source_job.save()
    automation = SourceAutomation.objects.create(
        name="Unfinished maintenance",
        run_as=source_job.requested_by,
        first_run_at=timezone.now(),
        next_run_at=timezone.now() + timedelta(days=1),
        catalog_scope="unfinished",
        rebuild_updated=True,
    )
    run = AutomationRun.objects.create(
        automation=automation,
        due_at=timezone.now(),
        state="queued",
        job=source_job,
        rebuild_updated=True,
    )
    snapshot = SimpleNamespace(entry=entry, book=book)
    ownership = SimpleNamespace(job_id=source_job.pk)
    outcome = rebuild_updated_source(ownership, snapshot)
    assert not outcome["error_code"]
    assert rebuild_updated_source(ownership, snapshot) == outcome
    from apps.processing.job_models import BackgroundJob

    job = BackgroundJob.objects.get(pk=outcome["operation_id"])
    book.refresh_from_db()
    assert job.automation_run == run and job.input["preserve_publication"]
    assert book.state == "published"
