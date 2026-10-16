from uuid import uuid5

import pytest
from apps.catalog.models import Book, UserBook
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.automations.processing import (
    dispatch_automation_sources,
    enqueue_selected_source,
)
from apps.processing.automations.scheduler import run_automation_tick
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.attempts import claim_attempt
from apps.processing.jobs.controls import request_stop, resume_job
from automation_fixtures import NOW
from test_source_discovery import archive_html, controlled_replies, execute

pytestmark = pytest.mark.django_db


@pytest.fixture
def scheduled_run(automation, tmp_path, settings):
    settings.RUNTIME_STORAGE_DIR = tmp_path
    automation.processing_limit = 2
    automation.save()
    return run_automation_tick(NOW)[0]


def test_discovery_schedules_only_bounded_unlinked_sources(
    scheduled_run, monkeypatch, client
):
    body = archive_html(1) + archive_html(2) + archive_html(3)
    controlled_replies(monkeypatch, [(200, {}, body)])
    execute(scheduled_run.job)
    children = scheduled_run.processing_jobs.all()
    assert scheduled_run.job.state == "succeeded" and children.count() == 2
    assert all(
        job.kind == "process_source" and job.state == "queued" for job in children
    )
    assert not Book.objects.exists() and not UserBook.objects.exists()
    client.force_login(scheduled_run.automation.run_as)
    path = f"/api/v1/manage/automations/{scheduled_run.automation_id}/runs/"
    history = client.get(path)
    assert history.status_code == 200
    entry = history.json()["entries"][0]
    assert entry["processing_count"] == entry["processing_active"] == 2
    assert entry["processing_rejected"] == 0 and "checkpoint" not in entry
    jobs = client.get(f"/api/v1/manage/jobs/?automation_run={scheduled_run.pk}").json()
    assert {row["id"] for row in jobs["entries"]} == {str(job.pk) for job in children}


def test_pause_after_first_child_commits_outcomes_and_resumes_without_duplicates(
    scheduled_run, monkeypatch
):
    controlled_replies(monkeypatch, [(200, {}, archive_html(1) + archive_html(2))])

    def pause_after_enqueue(ownership, selection, run):
        child = enqueue_selected_source(ownership, selection, run)
        request_stop(ownership.job_id, "pause")
        return child

    monkeypatch.setattr(
        "apps.processing.automations.processing.enqueue_selected_source",
        pause_after_enqueue,
    )
    execute(scheduled_run.job)
    assert (
        scheduled_run.job.state == "paused"
        and scheduled_run.processing_jobs.count() == 1
    )
    monkeypatch.setattr(
        "apps.processing.automations.processing.enqueue_selected_source",
        enqueue_selected_source,
    )
    adapter = controlled_replies(monkeypatch, [])
    resume_job(scheduled_run.job_id)
    scheduled_run.job.refresh_from_db()
    execute(scheduled_run.job)
    assert (
        scheduled_run.job.state == "succeeded"
        and scheduled_run.processing_jobs.count() == 2
    )
    assert not adapter.calls


def prepared_selection(run):
    entry = SourceCatalogEntry.objects.create(
        source_url="https://source.test/books/replay/", title="পুনরায় চালু"
    )
    selection = {"id": str(entry.pk), "revision": entry.updated_at.isoformat()}
    ownership = claim_attempt(run.job.dispatches.get().pk)
    run.job.refresh_from_db()
    run.job.checkpoint = {"automation_selections": [selection]}
    run.job.save()
    return ownership, selection


def test_child_commit_before_parent_checkpoint_reuses_original_command(scheduled_run):
    ownership, selection = prepared_selection(scheduled_run)
    child = enqueue_selected_source(ownership, selection, scheduled_run)
    assert dispatch_automation_sources(ownership)
    assert scheduled_run.processing_jobs.count() == 1
    assert child.pk == uuid5(scheduled_run.pk, selection["id"])
    assert child.dispatches.count() == 1


def test_deleted_selection_is_a_recorded_failure_without_aborting_the_batch(
    scheduled_run,
):
    ownership, selection = prepared_selection(scheduled_run)
    SourceCatalogEntry.objects.filter(pk=selection["id"]).delete()
    assert dispatch_automation_sources(ownership)
    scheduled_run.job.refresh_from_db()
    assert scheduled_run.job.checkpoint["automation_rejected_count"] == 1
    assert (
        scheduled_run.job.checkpoint["automation_outcomes"][selection["id"]][
            "error_code"
        ]
        == "source_record_missing"
    )


def test_stop_during_child_claim_is_committed_without_starting_a_child(scheduled_run):
    ownership, selection = prepared_selection(scheduled_run)
    request_stop(scheduled_run.job_id, "pause")
    assert enqueue_selected_source(ownership, selection, scheduled_run) is None
    scheduled_run.job.refresh_from_db()
    assert (
        scheduled_run.job.state == "paused"
        and not scheduled_run.processing_jobs.exists()
    )


def test_changed_source_snapshot_rejects_child_without_replacing_input(scheduled_run):
    ownership, selection = prepared_selection(scheduled_run)
    entry = SourceCatalogEntry.objects.get(pk=selection["id"])
    entry.title = "বদলে যাওয়া তথ্য"
    entry.save()
    assert dispatch_automation_sources(ownership)
    assert not scheduled_run.processing_jobs.exists()
    scheduled_run.job.refresh_from_db()
    assert scheduled_run.job.checkpoint["automation_rejected_count"] == 1


def test_changed_configuration_stops_processing_dispatch(scheduled_run, settings):
    from apps.processing.jobs.execution_errors import ExecutionFailure

    ownership, selection = prepared_selection(scheduled_run)
    settings.SOURCE_SITE_CATALOG_URL = "https://source.test/different/"
    with pytest.raises(ExecutionFailure, match="source_configuration_changed"):
        enqueue_selected_source(ownership, selection, scheduled_run)
    assert not scheduled_run.processing_jobs.exists()


def test_disabled_automatic_processing_only_discovers(scheduled_run, monkeypatch):
    scheduled_run.processing_limit = 0
    scheduled_run.save()
    controlled_replies(monkeypatch, [(200, {}, archive_html(1))])
    execute(scheduled_run.job)
    assert (
        scheduled_run.job.state == "succeeded"
        and not scheduled_run.processing_jobs.exists()
    )
    assert BackgroundJob.objects.count() == 1
