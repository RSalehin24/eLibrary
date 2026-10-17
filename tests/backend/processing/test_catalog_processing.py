from contextlib import nullcontext
from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book
from apps.ingestion.catalog_processing.commands import request_catalog_processing
from apps.ingestion.catalog_processing.queries import catalog_processing_options
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_processing.commands import request_source_processing
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.controls import request_stop, resume_job
from apps.processing.jobs.requests import JobStateConflict
from apps.processing.jobs.worker import run_background_job
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalog_actor(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_CATALOG_URL = "https://source.test/books/"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    return User.objects.create_user(email="catalog-manager@library.test", is_staff=True)


def source(number):
    return SourceCatalogEntry.objects.create(
        source_url=f"https://source.test/books/story-{number}/", title=f"Story {number}"
    )


def command():
    return {
        "operation_id": uuid4(),
        "configuration_revision": catalog_processing_options()[
            "configuration_revision"
        ],
    }


def execute(job):
    run_background_job(
        job.dispatches.get(generation=job.generation).pk, lambda _: nullcontext()
    )
    job.refresh_from_db()


def test_process_all_queues_more_than_one_hundred_books_in_durable_batches(
    catalog_actor,
):
    for number in range(105):
        source(number)
    job = request_catalog_processing(catalog_actor, command())
    execute(job)
    assert job.state == "succeeded"
    assert job.checkpoint["bulk_queued"] == job.checkpoint["bulk_total"] == 105
    assert (
        job.child_jobs.count() == 105
        and job.child_jobs.filter(state="queued").count() == 105
    )
    assert not Book.objects.exists()


def test_process_all_skips_linked_active_and_failed_sources(catalog_actor):
    linked = source(1)
    linked.catalog_book = Book.objects.create(title="Existing")
    linked.save()
    active, failed, eligible = source(2), source(3), source(4)
    request_source_processing(catalog_actor, (uuid4(), active.pk), active.updated_at)
    failed_job = request_source_processing(
        catalog_actor, (uuid4(), failed.pk), failed.updated_at
    )
    BackgroundJob.objects.filter(pk=failed_job.pk).update(
        state="failed", finished_at=timezone.now()
    )
    assert catalog_processing_options()["eligible_sources"] == 1
    job = request_catalog_processing(catalog_actor, command())
    execute(job)
    assert list(job.child_jobs.values_list("source_record_id", flat=True)) == [
        eligible.pk
    ]


def test_process_all_reuses_operation_ids_and_rejects_another_active_batch(
    catalog_actor,
):
    values = command()
    job = request_catalog_processing(catalog_actor, values)
    assert request_catalog_processing(catalog_actor, values).pk == job.pk
    with pytest.raises(JobStateConflict):
        request_catalog_processing(catalog_actor, command())
    assert BackgroundJob.objects.count() == 1


def test_pause_after_child_commit_resumes_without_duplicate_work(
    catalog_actor, monkeypatch
):
    from apps.ingestion.catalog_processing import worker

    first, second = source(1), source(2)
    job = request_catalog_processing(catalog_actor, command())
    save = worker.save_catalog_outcome

    def pause(ownership, selection, error_code):
        request_stop(job.pk, "pause")
        return save(ownership, selection, error_code)

    monkeypatch.setattr(worker, "save_catalog_outcome", pause)
    execute(job)
    assert job.state == "paused" and job.child_jobs.count() == 1
    monkeypatch.setattr(worker, "save_catalog_outcome", save)
    resume_job(job.pk)
    job.refresh_from_db()
    execute(job)
    assert job.state == "succeeded" and job.checkpoint["bulk_queued"] == 2
    assert set(job.child_jobs.values_list("source_record_id", flat=True)) == {
        first.pk,
        second.pk,
    }


def test_process_all_reports_invalid_source_without_aborting_other_books(catalog_actor):
    invalid = source(1)
    invalid.source_url = "https://unrelated.test/books/story/"
    invalid.save()
    source(2)
    job = request_catalog_processing(catalog_actor, command())
    execute(job)
    assert job.state == "succeeded" and job.checkpoint["bulk_queued"] == 1
    assert job.checkpoint["bulk_rejected"] == 1
    assert job.checkpoint["bulk_errors"][0]["source_id"] == str(invalid.pk)


@pytest.mark.parametrize("change", ["permission", "configuration"])
def test_bulk_worker_rechecks_authority_before_creating_children(
    catalog_actor, settings, change
):
    source(1)
    job = request_catalog_processing(catalog_actor, command())
    if change == "permission":
        catalog_actor.is_staff = False
        catalog_actor.save()
    else:
        settings.SOURCE_SITE_CATALOG_URL = "https://source.test/changed/"
    execute(job)
    assert job.state == "failed" and not job.child_jobs.exists()


def test_process_all_api_is_private_csrf_protected_and_tracks_children(
    catalog_actor, client
):
    client.force_login(catalog_actor)
    path = "/api/v1/manage/sources/process-all/"
    response = client.get(path)
    assert (
        response.status_code == 200 and response["Cache-Control"] == "private, no-store"
    )
    source(1)
    response = client.post(path, command(), content_type="application/json")
    assert response.status_code == 202
    job = BackgroundJob.objects.get(pk=response.json()["operation_id"])
    execute(job)
    children = client.get(f"/api/v1/manage/jobs/?parent_job={job.pk}").json()
    assert children["pagination"]["total_count"] == 1
    detail = client.get(f"/api/v1/manage/jobs/{job.pk}/").json()
    assert detail["bulk_queued"] == 1 and detail["kind"] == "process_catalog"


def test_reader_and_missing_csrf_never_create_a_batch(catalog_actor):
    from django.test import Client

    client = Client(enforce_csrf_checks=True)
    client.force_login(catalog_actor)
    path = "/api/v1/manage/sources/process-all/"
    assert (
        client.post(path, command(), content_type="application/json").status_code == 403
    )
    reader = User.objects.create_user(email="bulk-reader@library.test")
    client.force_login(reader)
    assert client.get(path).status_code == 403
    assert not BackgroundJob.objects.exists()


def test_missing_source_configuration_disables_bulk_options(
    catalog_actor, settings, client
):
    settings.SOURCE_SITE_HOST = ""
    client.force_login(catalog_actor)
    response = client.get("/api/v1/manage/sources/process-all/")
    assert (
        response.status_code == 200
        and response.json()["configuration_revision"] is None
    )


def test_scheduled_full_scan_creates_one_process_all_parent(
    automation, monkeypatch, tmp_path
):
    from apps.processing.automations.api import automation_runs
    from apps.processing.automations.scheduler import run_automation_tick
    from automation_fixtures import NOW
    from django.test import override_settings
    from test_source_discovery import archive_html, controlled_replies

    automation.fetch_all = automation.process_all = True
    automation.save()
    run = run_automation_tick(NOW)[0]
    controlled_replies(monkeypatch, [(200, {}, archive_html(1))])
    with override_settings(RUNTIME_STORAGE_DIR=tmp_path):
        execute(run.job)
    assert run.job.state == "succeeded" and run.process_all
    assert run.job.input["command"]["fetch_all"]
    parent = BackgroundJob.objects.get(kind="process_catalog", automation_run=run)
    execute(parent)
    assert parent.state == "succeeded" and parent.child_jobs.count() == 1
    history = automation_runs(automation).get()
    assert history.processing_count == 1 and history.processing_active == 1
