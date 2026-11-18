from rest_framework import status
from rest_framework.response import Response

from apps.ingestion.models import CatalogCurationRun, CatalogCurationTrigger
from apps.ingestion.services.curation import (
    ACTIVE_RUN_STATUSES,
    ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES,
    get_source_catalog_refresh_state,
)


def active_automation_run():
    return (
        CatalogCurationRun.objects.filter(trigger=CatalogCurationTrigger.SCHEDULED, status__in=ACTIVE_RUN_STATUSES)
        .order_by("-created_at")
        .first()
    )


def automation_manual_creation_locked_response():
    if not active_automation_run():
        return None
    return Response(
        {
            "detail": (
                "Automation is currently syncing the catalog and creating books. "
                "Manual book creation is temporarily disabled until it finishes."
            )
        },
        status=status.HTTP_409_CONFLICT,
    )


def source_catalog_sync_locked_response():
    sync_state = get_source_catalog_refresh_state()
    if sync_state.status not in ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES:
        return None
    return Response(
        {
            "detail": "Catalog sync is currently running. Manual catalog actions are disabled until it finishes."
        },
        status=status.HTTP_409_CONFLICT,
    )


__all__ = [
    "active_automation_run",
    "automation_manual_creation_locked_response",
    "source_catalog_sync_locked_response",
]
