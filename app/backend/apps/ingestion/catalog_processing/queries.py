from django.db.models import Exists, OuterRef
from rest_framework.exceptions import PermissionDenied

from apps.ingestion.source_discovery.configuration import discovery_configuration
from apps.ingestion.source_workspace.queries import source_entries
from apps.processing.job_models import (
    SOURCE_ACTIVE_STATES,
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
)
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from apps.processing.jobs.requests import require_processing_manager


def eligible_catalog_entries():
    failures = BackgroundJob.objects.filter(
        source_record_id=OuterRef("pk"), state=BackgroundJobState.FAILED
    )
    return (
        source_entries({"q": "", "status": "unlinked"})
        .annotate(has_failure=Exists(failures))
        .filter(active_operation_id__isnull=True, has_failure=False)
    )


def current_catalog_job(identifier):
    job = BackgroundJob.objects.select_related("requested_by").get(
        pk=identifier, kind=BackgroundJobKind.PROCESS_CATALOG
    )
    try:
        if job.requested_by is None:
            raise PermissionDenied()
        require_processing_manager(job.requested_by)
    except PermissionDenied:
        raise ExecutionFailure(FailureKind.PERMANENT, "permission_revoked") from None
    if (
        job.input["command"]["configuration_revision"]
        != discovery_configuration()["configuration_revision"]
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_configuration_changed")
    return job


def catalog_processing_options():
    try:
        revision = discovery_configuration()["configuration_revision"]
    except ExecutionFailure:
        revision = None
    jobs = BackgroundJob.objects.filter(kind=BackgroundJobKind.PROCESS_CATALOG)
    return {
        "configuration_revision": revision,
        "total_sources": source_entries({"q": "", "status": "all"}).count(),
        "eligible_sources": eligible_catalog_entries().count(),
        "active_operation_id": jobs.filter(state__in=SOURCE_ACTIVE_STATES)
        .values_list("id", flat=True)
        .first(),
        "latest_operation_id": jobs.values_list("id", flat=True).first(),
    }
