from datetime import timedelta
from uuid import uuid5

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.catalog.models import Book
from apps.processing.job_models import BackgroundJob

from .classification import VALIDATOR_VERSION
from .regeneration import request_book_regeneration


@transaction.atomic
def queue_quality_repair(previous, evidence):
    if previous.requested_by is None:
        return {"repair_error": "permission_revoked"}
    identifier = uuid5(previous.pk, f"source-validator:{VALIDATOR_VERSION}")
    existing = BackgroundJob.objects.filter(pk=identifier).first()
    if existing:
        return {"repair_operation_id": str(existing.pk)}
    book = Book.objects.get(pk=previous.book_id)
    try:
        job = request_book_regeneration(
            previous.requested_by,
            book.pk,
            {
                "operation_id": identifier,
                "expected_updated_at": book.updated_at,
            },
        )
    except APIException as error:
        return {"repair_error": error.default_code}
    classification = evidence.get("classification", "unknown_layout")
    job.state, job.error_code = (
        "retry_wait",
        "source_description_only"
        if classification == "description_only"
        else "source_layout_unknown",
    )
    job.available_at = timezone.now() + timedelta(hours=6)
    job.save(update_fields=["state", "error_code", "available_at", "updated_at"])
    job.dispatches.update(available_at=job.available_at)
    return {"repair_operation_id": str(job.pk)}
