from apps.catalog.content_quality import mark_source_verified, quarantine_book
from apps.catalog.models import Book
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .documents import read_source_result
from .quality_repair import queue_quality_repair
from .verification import source_verification


def audit_source_publication(job, apply=False):
    if not job.checkpoint.get("document_ref"):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_verification_missing")
    evidence = source_verification(
        read_source_result(job.pk, job.checkpoint["document_ref"])
    )
    result = {
        "operation_id": str(job.pk),
        "book_id": str(job.book_id),
        "title": job.book.title,
        "verified": evidence["verified"],
        "classification": evidence["classification"],
        "issues": evidence["issues"],
    }
    if apply and not evidence["verified"]:
        quarantine_book(job.book, evidence, actor=job.requested_by)
        result.update(queue_quality_repair(job, evidence))
    if apply and evidence["verified"]:
        mark_source_verified(job.book, evidence)
        Book.objects.filter(pk=job.book_id, updated_at=job.book.updated_at).update(
            source_quality_state="verified",
            raw_scraped_metadata=job.book.raw_scraped_metadata,
        )
    return result


def published_source_operations():
    return (
        BackgroundJob.objects.filter(
            kind="process_source",
            state="succeeded",
            book__state="published",
            book__deleted_at__isnull=True,
        )
        .select_related("book", "requested_by")
        .order_by("book_id", "-created_at")
        .distinct("book_id")
    )
