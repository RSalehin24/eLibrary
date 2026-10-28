from datetime import timedelta

from apps.catalog.models import GeneratedAssetType
from apps.ingestion.models import JobStatus, SubmissionStatus

REUSABLE_SUBMISSION_STATUSES = (
    SubmissionStatus.PENDING_RESOLUTION,
    SubmissionStatus.QUEUED,
    SubmissionStatus.PROCESSING,
    SubmissionStatus.READY,
)

SUBMISSION_PAYLOAD_KEYS_TO_SHARE = (
    "served_from_database",
    "existing_book_source",
    "linked_book_slug",
    "source_page_metadata",
    "normalized_url",
    "scraped_preview",
)

ACTIVE_JOB_STATUSES = (JobStatus.QUEUED, JobStatus.PROCESSING)

JOB_CANCEL_MESSAGE = "Stopped by user."

REQUEST_DELETE_MESSAGE = "Deleted by user."

REQUIRED_GENERATED_ASSET_TYPES = (GeneratedAssetType.HTML, GeneratedAssetType.EPUB)

GENERATED_ASSET_LABELS = {
    GeneratedAssetType.HTML: "HTML",
    GeneratedAssetType.EPUB: "EPUB",
}

MAX_PROCESSING_JOB_ATTEMPTS = 3

STALE_PROCESSING_JOB_AFTER = timedelta(minutes=20)

STALE_PROCESSING_RETRY_MESSAGE = (
    "Processing exceeded the recovery window and was retried automatically."
)

STALE_PROCESSING_FAILURE_MESSAGE = "Processing exceeded the recovery window and failed after the maximum retry attempts."

PROCESSING_RETRY_MESSAGE_TEMPLATE = "Processing failed on attempt {attempt} of {max_attempts} and will retry automatically."

RETRY_PAYLOAD_RESET_KEYS = (
    "served_from_database",
    "existing_book_source",
    "linked_book_slug",
)
