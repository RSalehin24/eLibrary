import argparse
import json
import os
import sys
from datetime import timedelta
from uuid import UUID, uuid4

import django
from seed_platform import pending_asset, require_isolated_deployment


def fixture_actor(fixture):
    from apps.accounts.models import User

    return User.objects.get(pk=fixture["administrator"]["id"])


def create_job(fixture, asset=None):
    from apps.processing.jobs.requests import PreparationRequest, request_preparation

    asset = asset or pending_asset()
    return request_preparation(
        fixture_actor(fixture), PreparationRequest(uuid4(), asset.pk, asset.updated_at)
    )


def owned_fixture_job(fixture, identifier):
    from apps.processing.job_models import BackgroundJob

    return BackgroundJob.objects.get(
        pk=identifier, requested_by=fixture_actor(fixture), kind="prepare_epub"
    )


def snapshot(job):
    from apps.access.publication_models import PreparedPublication

    return {
        "id": str(job.pk),
        "state": job.state,
        "attempt_count": job.attempt_count,
        "checkpoint_saved": bool(job.checkpoint),
        "error_code": job.error_code,
        "dispatch_pending": job.dispatches.filter(state="pending").exists(),
        "dispatch_published": job.dispatches.filter(state="published").exists(),
        "dispatch_failures": sum(
            job.dispatches.values_list("failure_count", flat=True)
        ),
        "updated_at": job.updated_at.isoformat(),
        "active_stage": job.active_attempt.stage if job.active_attempt_id else None,
        "prepared_publications": PreparedPublication.objects.filter(
            checksum=job.checkpoint.get("checksum"), state="ready"
        ).count(),
    }


def duplicate_delivery(job):
    from config.celery import app

    dispatch = job.dispatches.order_by("created_at").first()
    for _ in range(2):
        app.send_task(
            "apps.processing.tasks.run_background_job_task",
            args=[str(dispatch.pk)],
            queue="processing",
            delivery_mode=2,
            ignore_result=True,
        )


def interrupted_job(fixture):
    from apps.processing.job_models import JobAttempt
    from apps.processing.jobs.attempts import checkpoint_attempt, claim_attempt
    from django.utils import timezone

    job = create_job(fixture)
    ownership = claim_attempt(job.dispatches.get().pk)
    assert checkpoint_attempt(ownership, {"fixture": "persisted"}, "fixture_checkpoint")
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        heartbeat_at=timezone.now() - timedelta(seconds=181)
    )
    job.refresh_from_db()
    return job


def paused_job(fixture):
    from apps.processing.job_models import RequestedJobAction
    from apps.processing.jobs.attempts import checkpoint_attempt, claim_attempt
    from apps.processing.jobs.controls import request_stop

    job = create_job(fixture)
    ownership = claim_attempt(job.dispatches.get().pk)
    request_stop(job.pk, RequestedJobAction.PAUSE)
    assert not checkpoint_attempt(
        ownership, {"fixture": "persisted"}, "fixture_checkpoint"
    )
    job.refresh_from_db()
    return job


def main():
    os.umask(0o027)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    require_isolated_deployment()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "create",
            "create_interruptible",
            "snapshot",
            "duplicate",
            "interrupted",
            "paused",
        ],
    )
    parser.add_argument("--identifier", type=UUID)
    arguments = parser.parse_args()
    fixture = json.load(sys.stdin)
    if arguments.action == "create_interruptible":
        from interruption_fixture import interruptible_asset

        job = create_job(fixture, interruptible_asset())
    elif arguments.action == "paused":
        job = paused_job(fixture)
    elif arguments.action in {"create", "interrupted"}:
        job = (
            interrupted_job(fixture)
            if arguments.action == "interrupted"
            else create_job(fixture)
        )
    else:
        job = owned_fixture_job(fixture, arguments.identifier)
    if arguments.action == "duplicate":
        duplicate_delivery(job)
    print(json.dumps(snapshot(job)))


if __name__ == "__main__":
    main()
