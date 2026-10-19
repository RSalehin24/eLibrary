from apps.catalog.models import CuratedDocumentStatus
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .asset_publication import publish_source_assets
from .curation import curate_source_job
from .documents import read_source_result, write_source_result
from .editions import record_source_evidence
from .export_verification import require_verified_exports
from .exports import generated_source_assets
from .persistence import persist_source_book
from .publication import completed_source_publication, publish_verified_source
from .queries import current_source_job
from .reading_preparation import prepare_source_reading
from .summary import source_summary
from .verification import source_verification


def source_result(ownership, job):
    reference = job.checkpoint.get("document_ref")
    if reference:
        result, checkpoint = read_source_result(job.pk, reference), job.checkpoint
    else:
        result, checkpoint = curate_source_job(ownership, job)
        reference = write_source_result(job.pk, result)
    if not checkpoint_attempt(
        ownership,
        {
            **checkpoint,
            "document_ref": reference,
            "source_summary": source_summary(result),
        },
        "source_curated",
    ):
        return None
    return result


def require_complete_source(result):
    title = result["projection"].get("book_title", "")
    snapshot = result.get("source_snapshot", {})
    raw = snapshot.get("raw_scrape_payload", {})
    classification = source_verification(result)["classification"]
    if classification == "unavailable_content":
        raise ExecutionFailure(FailureKind.TRANSIENT, "source_content_unavailable")
    if classification in {"description_only", "unknown_layout"}:
        code = (
            "source_description_only"
            if classification == "description_only"
            else "source_layout_unknown"
        )
        raise ExecutionFailure(FailureKind.TRANSIENT, code)
    items = raw.get("content_items", [])
    if items and any(item.get("has_content", False) is None for item in items):
        raise ExecutionFailure(FailureKind.TRANSIENT, "source_content_unavailable")
    if (
        not isinstance(title, str)
        or not title.strip()
        or title == "Book Title"
        or len(title) > 255
    ):
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_metadata_incomplete")
    if (
        result["status"] != CuratedDocumentStatus.VALIDATED
        or not source_verification(result)["verified"]
    ):
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_content_incomplete")


def source_book(ownership, result):
    job = current_source_job(ownership.job_id)
    if job.book_id:
        return job.book
    return persist_source_book(ownership, result)


def export_source_book(ownership, result):
    job = current_source_job(ownership.job_id)
    if (
        job.checkpoint.get("assets_published") or job.checkpoint.get("staged_assets")
    ) and job.checkpoint.get("exports_verified"):
        return True
    if not checkpoint_attempt(ownership, job.checkpoint, "generating_exports"):
        return False
    paths = generated_source_assets(ownership, result)
    require_verified_exports(result, paths)
    current = current_source_job(ownership.job_id)
    if not checkpoint_attempt(
        ownership,
        {**current.checkpoint, "exports_verified": True},
        "source_exports_generated",
    ):
        return False
    publish_source_assets(ownership, paths)
    return True


def execute_source_processing(ownership):
    job = current_source_job(ownership.job_id)
    if job.checkpoint.get("auto_published"):
        return completed_source_publication(ownership)
    result = source_result(ownership, job)
    if result is None:
        return False
    current = current_source_job(ownership.job_id)
    record_source_evidence(
        current, source_verification(result), current.checkpoint.get("document_ref", "")
    )
    require_complete_source(result)
    source_book(ownership, result)
    if not export_source_book(ownership, result):
        return False
    return prepare_source_reading(ownership) and publish_verified_source(ownership)


def run_source_processing(ownership):
    try:
        return execute_source_processing(ownership)
    except OSError:
        raise ExecutionFailure(
            FailureKind.TRANSIENT, "source_storage_unavailable"
        ) from None
