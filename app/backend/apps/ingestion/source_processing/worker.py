from apps.catalog.models import CuratedDocumentStatus
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .asset_publication import publish_source_assets
from .curation import curate_source_job
from .exports import generated_source_assets
from .persistence import persist_source_book, source_duplicates
from .queries import current_source_job
from .reading_preparation import prepare_source_reading
from .storage import read_artifact, write_artifact
from .summary import source_summary


def source_result(ownership, job):
    reference = job.checkpoint.get("document_ref")
    if reference:
        result, checkpoint = read_artifact(job.pk, reference), job.checkpoint
    else:
        result, checkpoint = curate_source_job(ownership, job)
        reference = write_artifact(job.pk, result)
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
    if (
        not isinstance(title, str)
        or not title.strip()
        or title == "Book Title"
        or len(title) > 255
    ):
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_metadata_incomplete")
    if result["status"] != CuratedDocumentStatus.VALIDATED:
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_content_incomplete")


def source_book(ownership, result):
    job = current_source_job(ownership.job_id)
    if job.book_id:
        return job.book
    book = persist_source_book(ownership, result)
    if book is not None:
        return book
    checkpoint = {
        **job.checkpoint,
        "duplicate_book_ids": [
            str(identifier) for identifier in source_duplicates(result)
        ],
    }
    if not checkpoint_attempt(ownership, checkpoint, "source_duplicate"):
        return None
    raise ExecutionFailure(FailureKind.UNCERTAIN, "source_duplicate")


def export_source_book(ownership, result):
    job = current_source_job(ownership.job_id)
    if job.checkpoint.get("assets_published"):
        return True
    if not checkpoint_attempt(ownership, job.checkpoint, "generating_exports"):
        return False
    paths = generated_source_assets(ownership, result)
    current = current_source_job(ownership.job_id)
    if not checkpoint_attempt(
        ownership, current.checkpoint, "source_exports_generated"
    ):
        return False
    publish_source_assets(ownership, paths)
    return True


def execute_source_processing(ownership):
    job = current_source_job(ownership.job_id)
    result = source_result(ownership, job)
    if result is None:
        return False
    require_complete_source(result)
    if source_book(ownership, result) is None:
        return False
    if not export_source_book(ownership, result):
        return False
    return prepare_source_reading(ownership)


def run_source_processing(ownership):
    try:
        return execute_source_processing(ownership)
    except OSError:
        raise ExecutionFailure(
            FailureKind.TRANSIENT, "source_storage_unavailable"
        ) from None
