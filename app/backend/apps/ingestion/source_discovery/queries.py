from rest_framework.exceptions import PermissionDenied

from apps.processing.job_models import (
    SOURCE_ACTIVE_STATES,
    BackgroundJob,
    BackgroundJobKind,
)
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from apps.processing.jobs.requests import require_processing_manager

from .configuration import (
    DEFAULT_DISCOVERY_PAGES,
    MAX_DISCOVERY_PAGES,
    discovery_configuration,
)


def current_discovery_job(identifier):
    job = BackgroundJob.objects.select_related("requested_by").get(
        pk=identifier, kind=BackgroundJobKind.DISCOVER_SOURCE
    )
    try:
        if job.requested_by is None:
            raise PermissionDenied()
        require_processing_manager(job.requested_by)
    except PermissionDenied:
        raise ExecutionFailure(FailureKind.PERMANENT, "permission_revoked") from None
    if (
        job.input["command"]["configuration_revision"]
        != discovery_configuration(job.input["command"].get("catalog_scope", "all"))[
            "configuration_revision"
        ]
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_configuration_changed")
    return job


def discovery_options(catalog_scope="all"):
    configured = discovery_configuration(catalog_scope)
    jobs = BackgroundJob.objects.filter(kind=BackgroundJobKind.DISCOVER_SOURCE)
    return {
        **configured,
        "default_max_pages": DEFAULT_DISCOVERY_PAGES,
        "maximum_pages": MAX_DISCOVERY_PAGES,
        "active_operation_id": jobs.filter(state__in=SOURCE_ACTIVE_STATES)
        .values_list("id", flat=True)
        .first(),
        "latest_operation_id": jobs.values_list("id", flat=True).first(),
    }
