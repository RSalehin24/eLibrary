from contextlib import nullcontext
from uuid import uuid4

import pytest
from apps.access.publication_models import PreparedPublication
from apps.access.reading.preparation import prepare_epub_asset
from apps.processing.job_models import BackgroundJobState, RequestedJobAction
from apps.processing.jobs.controls import request_stop, resume_job
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from apps.processing.jobs.recovery import recover_stale_attempts
from apps.processing.jobs.worker import run_background_job
from django.utils import timezone

pytestmark = pytest.mark.django_db


def execute(job):
    run_background_job(
        job.dispatches.get(generation=job.generation).pk, lambda _: nullcontext()
    )
    job.refresh_from_db()


def test_worker_prepares_real_epub_and_repeated_delivery_does_not_repeat_work(
    preparation_job,
):
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.SUCCEEDED
    assert (
        preparation_job.checkpoint["checksum"]
        == PreparedPublication.objects.get().checksum
    )
    execute(preparation_job)
    assert preparation_job.attempts.count() == PreparedPublication.objects.count() == 1


@pytest.mark.parametrize("revocation", ["disabled", "grant", "deleted_book"])
def test_worker_checks_current_authorization_before_processing(
    preparation_job, revocation
):
    actor = preparation_job.requested_by
    if revocation == "disabled":
        actor.is_active = False
    elif revocation == "grant":
        actor.is_staff = False
    else:
        preparation_job.book.deleted_at = timezone.now()
        preparation_job.book.save()
    actor.save()
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.FAILED
    assert preparation_job.error_code in {"permission_revoked", "asset_unavailable"}
    assert not PreparedPublication.objects.exists()


def test_worker_rejects_an_asset_replaced_after_the_command(preparation_job):
    preparation_job.asset.save()
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.FAILED
    assert preparation_job.error_code == "asset_changed"
    assert not PreparedPublication.objects.exists()


def test_worker_records_invalid_epub_without_retry(preparation_job, tmp_path):
    (tmp_path / "job.epub").write_bytes(b"not an EPUB")
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.FAILED
    assert preparation_job.error_code == "invalid_epub"
    assert preparation_job.dispatches.count() == 1


def test_worker_records_missing_storage_without_retry(preparation_job, monkeypatch):
    from apps.access import storage

    monkeypatch.setattr(storage.Path, "exists", lambda _: False)
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.FAILED
    assert preparation_job.error_code == "asset_missing"


def test_worker_retries_transient_storage_failure(preparation_job, monkeypatch):
    from apps.processing.jobs import preparation

    def interrupted(_):
        raise OSError("synthetic storage outage")

    monkeypatch.setattr(preparation, "prepare_epub_asset", interrupted)
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.RETRY_WAIT
    assert preparation_job.error_code == "storage_unavailable"
    assert preparation_job.dispatches.count() == 2


def test_pause_during_preparation_is_confirmed_at_the_checkpoint_and_can_resume(
    preparation_job, monkeypatch
):
    from apps.processing.jobs import preparation

    def prepare_and_pause(asset):
        publication = prepare_epub_asset(asset)
        request_stop(preparation_job.pk, RequestedJobAction.PAUSE)
        return publication

    monkeypatch.setattr(preparation, "prepare_epub_asset", prepare_and_pause)
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.PAUSED
    assert preparation_job.checkpoint["publication_id"]
    monkeypatch.setattr(preparation, "prepare_epub_asset", prepare_epub_asset)
    preparation_job = resume_job(preparation_job.pk)
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.SUCCEEDED
    assert PreparedPublication.objects.count() == 1


def test_permission_revocation_during_preparation_prevents_success(
    preparation_job, monkeypatch
):
    from apps.processing.jobs import preparation

    def prepare_and_revoke(asset):
        publication = prepare_epub_asset(asset)
        actor = preparation_job.requested_by
        actor.is_active = False
        actor.save()
        return publication

    monkeypatch.setattr(preparation, "prepare_epub_asset", prepare_and_revoke)
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.FAILED
    assert preparation_job.error_code == "permission_revoked"
    assert PreparedPublication.objects.count() == 1


def test_unknown_dispatch_is_ignored_safely():
    run_background_job(uuid4(), lambda _: nullcontext())


def test_recovery_during_preparation_rejects_the_old_completion(
    preparation_job, monkeypatch
):
    from apps.processing.jobs import preparation

    def prepare_and_recover(asset):
        publication = prepare_epub_asset(asset)
        recover_stale_attempts(timezone.now())
        return publication

    monkeypatch.setattr(preparation, "prepare_epub_asset", prepare_and_recover)
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.RETRY_WAIT
    assert preparation_job.error_code == "worker_interrupted"
    assert PreparedPublication.objects.count() == 1


def test_cancellation_before_the_processing_unit_avoids_extraction(
    preparation_job, monkeypatch
):
    from apps.processing.jobs import worker

    original = worker.claim_attempt

    def claim_and_cancel(identifier):
        ownership = original(identifier)
        request_stop(preparation_job.pk, RequestedJobAction.CANCEL)
        return ownership

    monkeypatch.setattr(worker, "claim_attempt", claim_and_cancel)
    execute(preparation_job)
    assert preparation_job.state == BackgroundJobState.CANCELLED
    assert not PreparedPublication.objects.exists()


def test_a_heartbeat_failure_prevents_recording_success(preparation_job):
    from contextlib import contextmanager

    @contextmanager
    def interrupted(_):
        yield
        raise ExecutionFailure(FailureKind.TRANSIENT, "heartbeat_unavailable")

    run_background_job(preparation_job.dispatches.get().pk, interrupted)
    preparation_job.refresh_from_db()
    assert preparation_job.state == BackgroundJobState.RETRY_WAIT
    assert preparation_job.checkpoint["publication_id"]
    assert preparation_job.error_code == "heartbeat_unavailable"


def test_registered_celery_task_executes_the_persisted_dispatch_identifier(
    preparation_job,
):
    from apps.processing.jobs.broker import BACKGROUND_JOB_TASK
    from apps.processing.tasks import run_background_job_task

    assert run_background_job_task.name == BACKGROUND_JOB_TASK
    assert (
        run_background_job_task.acks_late
        and run_background_job_task.reject_on_worker_lost
    )
    assert run_background_job_task.ignore_result
    run_background_job_task.apply(args=[str(preparation_job.dispatches.get().pk)]).get()
    preparation_job.refresh_from_db()
    assert preparation_job.state == BackgroundJobState.SUCCEEDED
