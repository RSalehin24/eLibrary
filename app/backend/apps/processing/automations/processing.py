from uuid import uuid5

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.ingestion.catalog_processing.commands import request_catalog_processing
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_discovery.queries import current_discovery_job
from apps.ingestion.source_processing.commands import request_source_processing
from apps.ingestion.source_workspace.queries import source_entries
from apps.processing.automation_models import AutomationRun
from apps.processing.job_models import BackgroundJob, BackgroundJobState
from apps.processing.jobs.attempts import checkpoint_attempt, owned_job
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def automation_selections(job, run):
    if "automation_selections" in job.checkpoint:
        return job.checkpoint["automation_selections"]
    failures = BackgroundJob.objects.filter(
        source_record_id=OuterRef("pk"), state=BackgroundJobState.FAILED
    )
    entries = (
        source_entries({"q": "", "status": "unlinked"})
        .annotate(has_failure=Exists(failures))
        .filter(
            last_seen_at__gte=run.created_at,
            active_operation_id__isnull=True,
            has_failure=False,
        )[: run.processing_limit]
    )
    return [
        {"id": str(entry.pk), "revision": entry.updated_at.isoformat()}
        for entry in entries
    ]


@transaction.atomic
def enqueue_selected_source(ownership, selection, run):
    User.objects.select_for_update(no_key=True).get(pk=run.job.requested_by_id)
    parent = owned_job(ownership)
    current_discovery_job(parent.pk)
    if not checkpoint_attempt(
        ownership, parent.checkpoint, "scheduling_source_processing"
    ):
        return None
    entry = SourceCatalogEntry.objects.get(pk=selection["id"])
    job = request_source_processing(
        parent.requested_by,
        (uuid5(run.pk, selection["id"]), entry.pk),
        parse_datetime(selection["revision"]),
    )
    job.automation_run = run
    job.save(update_fields=["automation_run", "updated_at"])
    return job


@transaction.atomic
def dispatch_all_catalog(ownership, run):
    snapshot = current_discovery_job(ownership.job_id)
    User.objects.select_for_update(no_key=True).get(pk=snapshot.requested_by_id)
    parent = owned_job(ownership)
    if not checkpoint_attempt(
        ownership, parent.checkpoint, "scheduling_source_processing"
    ):
        return False
    try:
        batch = request_catalog_processing(
            parent.requested_by,
            {
                "operation_id": uuid5(run.pk, "process-all"),
                "configuration_revision": parent.input["command"][
                    "configuration_revision"
                ],
            },
            run,
        )
    except APIException:
        raise ExecutionFailure(
            FailureKind.TRANSIENT, "catalog_processing_already_active"
        ) from None
    return checkpoint_attempt(
        ownership,
        {**parent.checkpoint, "automation_batch_job_id": str(batch.pk)},
        "scheduling_source_processing",
    )


def dispatch_automation_sources(ownership):
    run = (
        AutomationRun.objects.select_related("job")
        .filter(job_id=ownership.job_id)
        .first()
    )
    if run is not None and run.process_all:
        return dispatch_all_catalog(ownership, run)
    if run is None or not run.processing_limit:
        return True
    parent = BackgroundJob.objects.get(pk=ownership.job_id)
    selections = automation_selections(parent, run)
    outcomes = dict(parent.checkpoint.get("automation_outcomes", {}))
    if not checkpoint_attempt(
        ownership,
        {**parent.checkpoint, "automation_selections": selections},
        "scheduling_source_processing",
    ):
        return False
    for selection in selections:
        if selection["id"] in outcomes:
            continue
        try:
            job = enqueue_selected_source(ownership, selection, run)
            if job is None:
                return False
            outcomes[selection["id"]] = {"job_id": str(job.pk), "error_code": ""}
        except APIException as error:
            outcomes[selection["id"]] = {
                "job_id": None,
                "error_code": error.default_code,
            }
        except SourceCatalogEntry.DoesNotExist:
            outcomes[selection["id"]] = {
                "job_id": None,
                "error_code": "source_record_missing",
            }
        parent.refresh_from_db()
        if not checkpoint_attempt(
            ownership,
            {
                **parent.checkpoint,
                "automation_outcomes": outcomes,
                "automation_selected_count": len(selections),
                "automation_rejected_count": sum(
                    bool(value["error_code"]) for value in outcomes.values()
                ),
            },
            "scheduling_source_processing",
        ):
            return False
    return True
