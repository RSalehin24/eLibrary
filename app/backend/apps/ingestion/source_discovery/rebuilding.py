from uuid import uuid5

from django.db import transaction
from rest_framework.exceptions import APIException

from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_processing.regeneration import request_book_regeneration
from apps.processing.automation_models import AutomationRun


@transaction.atomic
def rebuild_updated_source(ownership, snapshot):
    run = (
        AutomationRun.objects.select_related("job__requested_by")
        .filter(job_id=ownership.job_id, rebuild_updated=True)
        .first()
    )
    if run is None or run.job is None:
        return None
    entry = SourceCatalogEntry.objects.get(pk=snapshot.entry.pk)
    update = entry.raw_data.get("source_update", {})
    if update.get("status") != "available":
        return None
    identifier = uuid5(run.pk, str(entry.pk) + update["signature"])
    try:
        job = request_book_regeneration(
            run.job.requested_by,
            snapshot.book.pk,
            {
                "operation_id": identifier,
                "expected_updated_at": snapshot.book.updated_at,
            },
        )
    except APIException as error:
        return {"source_id": str(entry.pk), "error_code": error.default_code}
    job.automation_run = run
    job.save(update_fields=["automation_run", "updated_at"])
    return {"source_id": str(entry.pk), "operation_id": str(job.pk), "error_code": ""}
