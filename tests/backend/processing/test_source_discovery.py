from contextlib import nullcontext
from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_discovery.commands import request_source_discovery
from apps.ingestion.source_discovery.configuration import discovery_configuration
from apps.ingestion.source_processing.transport import ControlledSourceSession
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.controls import request_stop, resume_job
from apps.processing.jobs.requests import JobStateConflict
from apps.processing.jobs.worker import run_background_job
from source_transport_fixture import FixtureAdapter, fixture_request_slot

pytestmark = pytest.mark.django_db
CATALOG_URL = "https://source.test/books/"


@pytest.fixture
def discovery_job(settings, tmp_path):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_CATALOG_URL = CATALOG_URL
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    settings.RUNTIME_STORAGE_DIR = tmp_path
    actor = User.objects.create_user(
        email="source-discovery@library.test", is_staff=True
    )
    configuration = discovery_configuration()
    return request_source_discovery(
        actor,
        {
            "operation_id": uuid4(),
            "configuration_revision": configuration["configuration_revision"],
            "max_pages": 2,
        },
    )


def archive_html(number, next_url=None):
    link = (
        f'<a class="next page-numbers" href="{next_url}">পরের পাতা</a>'
        if next_url
        else ""
    )
    return f'<article><h2 class="entry-title"><a href="https://source.test/books/story-{number}/">গল্প {number}</a></h2></article>{link}'.encode()


def controlled_replies(monkeypatch, replies):
    adapter = FixtureAdapter(replies)

    def session(boundary):
        client = ControlledSourceSession(boundary, fixture_request_slot)
        client.mount("https://", adapter)
        return client

    monkeypatch.setattr(
        "apps.ingestion.source_discovery.worker.ControlledSourceSession", session
    )
    return adapter


def execute(job):
    run_background_job(
        job.dispatches.get(generation=job.generation).pk, lambda _: nullcontext()
    )
    job.refresh_from_db()


def test_discovery_collects_bounded_pages_without_creating_books_or_ownership(
    discovery_job, monkeypatch
):
    adapter = controlled_replies(
        monkeypatch,
        [
            (200, {}, archive_html(1, "https://source.test/books/page/2/")),
            (200, {}, archive_html(2, "https://source.test/books/page/3/")),
        ],
    )
    execute(discovery_job)
    assert (
        discovery_job.state == "succeeded" and SourceCatalogEntry.objects.count() == 2
    )
    assert (
        discovery_job.checkpoint["discovered_pages"]
        == discovery_job.checkpoint["discovered_entries"]
        == 2
    )
    assert discovery_job.checkpoint["more_pages_available"] and len(adapter.calls) == 2
    assert not Book.objects.exists() and not UserBook.objects.exists()


def test_discovery_idempotency_and_single_active_operation(discovery_job):
    values = {
        "operation_id": discovery_job.pk,
        "configuration_revision": discovery_configuration()["configuration_revision"],
        "max_pages": 2,
    }
    assert (
        request_source_discovery(discovery_job.requested_by, values).pk
        == discovery_job.pk
    )
    values["operation_id"] = uuid4()
    with pytest.raises(JobStateConflict):
        request_source_discovery(discovery_job.requested_by, values)
    assert BackgroundJob.objects.count() == 1 and discovery_job.dispatches.count() == 1


def test_unchanged_discovery_preserves_source_revision_and_catalog_link(
    discovery_job, monkeypatch
):
    book = Book.objects.create(title="আগের সম্পাদিত বই")
    entry = SourceCatalogEntry.objects.create(
        source_url="https://source.test/books/story-1/",
        title="গল্প 1",
        normalized_title="গল্প 1",
        normalized_display="গল্প 1",
        catalog_book=book,
    )
    before = entry.updated_at
    controlled_replies(monkeypatch, [(200, {}, archive_html(1))])
    execute(discovery_job)
    entry.refresh_from_db()
    assert entry.updated_at == before and entry.catalog_book_id == book.pk
    assert SourceCatalogEntry.objects.count() == 1


def test_changed_archive_metadata_updates_revision_but_preserves_catalog_data(
    discovery_job, monkeypatch
):
    book = Book.objects.create(title="অক্ষত বই", summary="সম্পাদকীয় লেখা")
    entry = SourceCatalogEntry.objects.create(
        source_url="https://source.test/books/story-1/",
        title="আগের নাম",
        catalog_book=book,
        raw_data={"manual_note": "kept"},
    )
    before = entry.updated_at
    controlled_replies(monkeypatch, [(200, {}, archive_html(1))])
    execute(discovery_job)
    entry.refresh_from_db()
    book.refresh_from_db()
    assert (
        entry.title == "গল্প 1"
        and entry.updated_at > before
        and entry.raw_data == {"manual_note": "kept"}
    )
    assert entry.catalog_book_id == book.pk and book.summary == "সম্পাদকীয় লেখা"


@pytest.mark.parametrize(
    "failure", ["configuration", "permission", "external_next", "login_page", "loop"]
)
def test_discovery_rejects_changed_authority_and_unsafe_or_incomplete_pages(
    discovery_job, settings, monkeypatch, failure
):
    if failure == "configuration":
        settings.SOURCE_SITE_CATALOG_URL = "https://source.test/catalog/"
    elif failure == "permission":
        actor = discovery_job.requested_by
        actor.is_staff = False
        actor.save()
    body = archive_html(1)
    if failure == "external_next":
        body = archive_html(1, "https://evil.test/private/")
    elif failure == "loop":
        body = archive_html(1, CATALOG_URL)
    elif failure == "login_page":
        body = b'<form><input type="password" /></form>'
    adapter = controlled_replies(monkeypatch, [(200, {}, body)])
    execute(discovery_job)
    assert discovery_job.state == "failed" and not SourceCatalogEntry.objects.exists()
    assert len(adapter.calls) == (
        0 if failure in {"configuration", "permission"} else 1
    )


def test_discovery_pauses_after_a_committed_page_and_resumes_at_the_next_page(
    discovery_job, monkeypatch
):
    from apps.ingestion.source_discovery.persistence import commit_discovery_page

    def pause(ownership, entries, checkpoint):
        saved = commit_discovery_page(ownership, entries, checkpoint)
        request_stop(discovery_job.pk, "pause")
        return saved

    adapter = controlled_replies(
        monkeypatch, [(200, {}, archive_html(1, "https://source.test/books/page/2/"))]
    )
    monkeypatch.setattr(
        "apps.ingestion.source_discovery.worker.commit_discovery_page", pause
    )
    execute(discovery_job)
    assert (
        discovery_job.state == "paused"
        and SourceCatalogEntry.objects.count() == 1
        and len(adapter.calls) == 1
    )
    monkeypatch.setattr(
        "apps.ingestion.source_discovery.worker.commit_discovery_page",
        commit_discovery_page,
    )
    adapter = controlled_replies(monkeypatch, [(200, {}, archive_html(2))])
    resume_job(discovery_job.pk)
    discovery_job.refresh_from_db()
    execute(discovery_job)
    assert (
        discovery_job.state == "succeeded" and SourceCatalogEntry.objects.count() == 2
    )
    assert adapter.calls[0][0].url.endswith("/page/2/")


def test_discovery_options_and_commands_are_private_and_role_checked(
    discovery_job, client
):
    path = "/api/v1/manage/sources/discovery/"
    client.force_login(discovery_job.requested_by)
    response = client.get(path)
    assert response.status_code == 200 and response.json()[
        "active_operation_id"
    ] == str(discovery_job.pk)
    assert (
        response["Cache-Control"] == "private, no-store"
        and response["X-Robots-Tag"] == "noindex"
    )
    options = response.json()
    accepted = client.post(
        path,
        {
            "operation_id": str(discovery_job.pk),
            "configuration_revision": options["configuration_revision"],
            "max_pages": 2,
        },
        content_type="application/json",
    )
    assert accepted.status_code == 202
    reader = User.objects.create_user(email="discovery-reader@library.test")
    client.force_login(reader)
    assert (
        client.get(path).status_code
        == client.post(path, {}, content_type="application/json").status_code
        == 403
    )
