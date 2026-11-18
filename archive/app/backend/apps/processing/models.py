import uuid
from datetime import time

from django.db import models

from apps.common.models import TimeStampedModel


def generate_processing_id():
    return str(uuid.uuid4())


class BookCreationRequestState(models.TextChoices):
    INITIAL = "initial", "Initial"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    CREATED = "created", "Created"
    PAUSED = "paused", "Paused"
    FAILED = "failed", "Failed"
    DUPLICATE = "duplicate", "Duplicate"
    DELETED = "deleted", "Deleted"


class BookCreationState(models.TextChoices):
    NOT_CREATED = "not_created", "Not created"
    INITIAL = "initial", "Initial"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    CREATED = "created", "Created"
    PAUSED = "paused", "Paused"
    FAILED = "failed", "Failed"
    DUPLICATE = "duplicate", "Duplicate"
    DELETED = "deleted", "Deleted"


class ProcessingAutomationKind(models.TextChoices):
    CATALOG = "catalog", "Catalog"
    INCOMPLETE = "incomplete", "Incomplete"


class ProcessingSyncStatus(models.TextChoices):
    IDLE = "idle", "Idle"
    SYNCING = "syncing", "Syncing"
    PAUSING = "pausing", "Pausing"
    PAUSED = "paused", "Paused"


class BookRecord(TimeStampedModel):
    id = models.CharField(primary_key=True, max_length=120, default=generate_processing_id)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=1000, unique=True)
    category = models.CharField(max_length=255)
    writer = models.CharField(max_length=255, blank=True)
    translator = models.CharField(max_length=255, blank=True)
    composer = models.CharField(max_length=255, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    book_creation_state = models.CharField(
        max_length=32,
        choices=BookCreationState.choices,
        default=BookCreationState.NOT_CREATED,
        db_index=True,
    )
    linked_book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="processing_book_records",
    )
    was_incomplete = models.BooleanField(default=False)
    resolved_from_incomplete = models.BooleanField(default=False)
    will_resolve_to_category = models.CharField(max_length=255, blank=True)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of_record = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="duplicate_records",
    )
    source_catalog_entry = models.ForeignKey(
        "ingestion.SourceCatalogEntry",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="processing_records",
    )

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class BookCreationRequest(TimeStampedModel):
    State = BookCreationRequestState

    id = models.CharField(primary_key=True, max_length=120, default=generate_processing_id)
    book_record = models.ForeignKey(
        BookRecord,
        on_delete=models.CASCADE,
        related_name="creation_requests",
    )
    state = models.CharField(
        max_length=32,
        choices=BookCreationRequestState.choices,
        default=BookCreationRequestState.INITIAL,
        db_index=True,
    )
    origin = models.CharField(
        max_length=16,
        choices=[
            ("user", "User"),
            ("curation", "Source curation"),
            ("automation", "Daily automation"),
        ],
        default="curation",
        db_index=True,
    )
    progress = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    is_resumed = models.BooleanField(default=False)
    is_confirmed_not_duplicate = models.BooleanField(default=False)
    force_generate = models.BooleanField(default=False)
    duplicate_of_request = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="duplicate_requests",
    )
    duplicate_of_record = models.ForeignKey(
        BookRecord,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="duplicate_creation_requests",
    )
    duplicate_confirmed = models.BooleanField(default=False)
    has_multi_page_toc = models.BooleanField(default=False, db_index=True)
    source_toc_page_count = models.PositiveIntegerField(default=1)
    fetched_toc_page_count = models.PositiveIntegerField(default=1)
    linked_book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="processing_creation_requests",
    )
    submission = models.OneToOneField(
        "ingestion.BookSubmission",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="processing_request",
    )
    pipeline_outcome = models.CharField(max_length=32, default=BookCreationRequestState.CREATED)

    class Meta:
        ordering = ["-updated_at", "-created_at", "id"]

    def __str__(self):
        return f"{self.book_record_id}: {self.state}"


class ProcessingSyncState(TimeStampedModel):
    singleton_key = models.CharField(max_length=32, unique=True, default="default")
    status = models.CharField(
        max_length=32,
        choices=ProcessingSyncStatus.choices,
        default=ProcessingSyncStatus.IDLE,
    )
    progress = models.JSONField(blank=True, null=True)
    remote_pages = models.JSONField(default=list, blank=True)
    page_index = models.PositiveIntegerField(default=0)
    fetched_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    appended_count = models.PositiveIntegerField(default=0)
    message = models.CharField(max_length=500, default="Ready to sync.")
    task_id = models.CharField(max_length=255, blank=True)
    queue_name = models.CharField(max_length=100, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ["singleton_key"]


class ProcessingAutomationSettings(TimeStampedModel):
    kind = models.CharField(
        max_length=32,
        choices=ProcessingAutomationKind.choices,
        unique=True,
    )
    enabled = models.BooleanField(default=False)
    interval = models.CharField(max_length=32, default="daily")
    time = models.TimeField(default=time(2, 0))
    saved = models.BooleanField(default=False)
    last_run_at = models.DateTimeField(blank=True, null=True)
    status_message = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["kind"]


class ProcessingUiDomainVersion(TimeStampedModel):
    domain = models.CharField(max_length=120, unique=True)
    version = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ["domain"]

    def __str__(self):
        return f"{self.domain}@{self.version}"


class ProcessingUiProjection(TimeStampedModel):
    key = models.CharField(max_length=120, unique=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


__all__ = [
    "BookCreationRequest",
    "BookCreationRequestState",
    "BookCreationState",
    "BookRecord",
    "ProcessingAutomationKind",
    "ProcessingAutomationSettings",
    "ProcessingUiDomainVersion",
    "ProcessingUiProjection",
    "ProcessingSyncState",
    "ProcessingSyncStatus",
]
