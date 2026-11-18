from django.db import models


class SubmissionInputType(models.TextChoices):
    URL = "url", "Direct URL"
    TITLE = "title", "Title query"
    CSV = "csv", "CSV import"


class ResolutionStatus(models.TextChoices):
    UNRESOLVED = "unresolved", "Unresolved"
    RESOLVED = "resolved", "Resolved"
    EXACT_MATCH = "exact_match", "Exact match"
    AMBIGUOUS = "ambiguous", "Ambiguous"
    REJECTED = "rejected", "Rejected"
    INVALID = "invalid", "Invalid"


class SubmissionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_RESOLUTION = "pending_resolution", "Pending resolution"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    NEEDS_REVIEW = "needs_review", "Needs review"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    DUPLICATE = "duplicate", "Duplicate candidate"
    DELETED = "deleted", "Deleted"


class JobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class JobType(models.TextChoices):
    RESOLUTION = "resolution", "Resolution"
    INGESTION = "ingestion", "Ingestion"
    REPROCESS = "reprocess", "Reprocess"


class DuplicateReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    DISMISSED = "dismissed", "Dismissed"
    MERGED = "merged", "Merged"


class CatalogCurationMode(models.TextChoices):
    PENDING = "pending", "Pending only"
    ALL = "all", "All tracked books"


class CatalogCurationTrigger(models.TextChoices):
    MANUAL = "manual", "Manual"
    SCHEDULED = "scheduled", "Scheduled"


class CatalogAutomationFrequency(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    BIWEEKLY = "biweekly", "Bi-weekly"
    MONTHLY = "monthly", "Monthly"
    BIMONTHLY = "bimonthly", "Bi-monthly"
    QUARTERLY = "quarterly", "Every 3 months"
    FOUR_MONTHLY = "four_monthly", "Every 4 months"
    HALF_YEARLY = "half_yearly", "Half-yearly"


class SourceCatalogRefreshStatus(models.TextChoices):
    IDLE = "idle", "Idle"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class SubmissionOrigin(models.TextChoices):
    USER = "user", "User"
    CURATION = "curation", "Source curation"
    AUTOMATION = "automation", "Daily automation"


__all__ = [
    "CatalogAutomationFrequency",
    "CatalogCurationMode",
    "CatalogCurationTrigger",
    "DuplicateReviewStatus",
    "JobStatus",
    "JobType",
    "ResolutionStatus",
    "SourceCatalogRefreshStatus",
    "SubmissionInputType",
    "SubmissionOrigin",
    "SubmissionStatus",
]
