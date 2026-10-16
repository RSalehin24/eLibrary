from typing import ClassVar

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class BackgroundJobKind(models.TextChoices):
    PREPARE_EPUB = "prepare_epub", "Prepare EPUB"
    DELIVER_KINDLE = "deliver_kindle", "Deliver to Kindle"
    ACCOUNT_MAIL = "account_mail", "Send account link"
    PROCESS_SOURCE = "process_source", "Process source book"
    DISCOVER_SOURCE = "discover_source", "Discover source catalog"


class BackgroundJobState(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    RETRY_WAIT = "retry_wait", "Waiting to retry"
    PAUSED = "paused", "Paused"
    CANCELLED = "cancelled", "Cancelled"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    NEEDS_ATTENTION = "needs_attention", "Needs attention"


class RequestedJobAction(models.TextChoices):
    NONE = "", "None"
    PAUSE = "pause", "Pause"
    CANCEL = "cancel", "Cancel"


SOURCE_ACTIVE_STATES = (
    BackgroundJobState.QUEUED,
    BackgroundJobState.RUNNING,
    BackgroundJobState.RETRY_WAIT,
    BackgroundJobState.PAUSED,
    BackgroundJobState.NEEDS_ATTENTION,
)


class BackgroundJob(UUIDPrimaryKeyModel, TimeStampedModel):
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="background_jobs",
    )
    book = models.ForeignKey(
        "catalog.Book",
        on_delete=models.PROTECT,
        related_name="background_jobs",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey(
        "catalog.GeneratedAsset",
        on_delete=models.PROTECT,
        related_name="background_jobs",
        null=True,
        blank=True,
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="account_mail_jobs",
    )
    source_record = models.ForeignKey(
        "ingestion.SourceCatalogEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="background_jobs",
    )
    automation_run = models.ForeignKey(
        "processing.AutomationRun",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processing_jobs",
    )
    kind = models.CharField(max_length=24, choices=BackgroundJobKind.choices)
    state = models.CharField(
        max_length=24,
        choices=BackgroundJobState.choices,
        default=BackgroundJobState.QUEUED,
    )
    requested_action = models.CharField(
        max_length=8,
        choices=RequestedJobAction.choices,
        default=RequestedJobAction.NONE,
        blank=True,
    )
    input = models.JSONField(default=dict)
    checkpoint = models.JSONField(default=dict)
    generation = models.PositiveIntegerField(default=1)
    attempt_count = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    available_at = models.DateTimeField()
    active_attempt = models.ForeignKey(
        "JobAttempt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_jobs",
    )
    error_code = models.CharField(max_length=64, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at", "-id"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["state", "available_at"], name="job_state_available_idx"
            )
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        kind="account_mail",
                        account__isnull=False,
                        book__isnull=True,
                        asset__isnull=True,
                        source_record__isnull=True,
                    )
                    | models.Q(
                        kind__in=["prepare_epub", "deliver_kindle"],
                        account__isnull=True,
                        book__isnull=False,
                        asset__isnull=False,
                        source_record__isnull=True,
                    )
                    | models.Q(
                        kind="process_source",
                        source_record__isnull=False,
                        account__isnull=True,
                    )
                    | models.Q(
                        kind="discover_source",
                        source_record__isnull=True,
                        account__isnull=True,
                        book__isnull=True,
                        asset__isnull=True,
                    )
                ),
                name="job_valid_domain_target",
            ),
            models.UniqueConstraint(
                fields=["source_record"],
                name="job_one_active_source",
                condition=models.Q(
                    kind="process_source",
                    state__in=SOURCE_ACTIVE_STATES,
                ),
            ),
            models.UniqueConstraint(
                fields=["kind"],
                name="job_one_active_discovery",
                condition=models.Q(
                    kind="discover_source", state__in=SOURCE_ACTIVE_STATES
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(max_attempts__gte=1, max_attempts__lte=10),
                name="job_valid_attempt_limit",
            ),
            models.CheckConstraint(
                condition=models.Q(generation__gte=1), name="job_positive_generation"
            ),
        ]


class JobAttempt(UUIDPrimaryKeyModel, TimeStampedModel):
    job = models.ForeignKey(
        BackgroundJob, on_delete=models.CASCADE, related_name="attempts"
    )
    number = models.PositiveIntegerField()
    generation = models.PositiveIntegerField()
    heartbeat_at = models.DateTimeField()
    stage = models.CharField(max_length=64, default="claimed")
    finished_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["job", "number"], name="job_attempt_number_unique"
            )
        ]


class DispatchState(models.TextChoices):
    PENDING = "pending", "Pending"
    LEASED = "leased", "Leased"
    PUBLISHED = "published", "Published"


class JobDispatch(UUIDPrimaryKeyModel, TimeStampedModel):
    job = models.ForeignKey(
        BackgroundJob, on_delete=models.CASCADE, related_name="dispatches"
    )
    generation = models.PositiveIntegerField()
    state = models.CharField(
        max_length=16, choices=DispatchState.choices, default=DispatchState.PENDING
    )
    available_at = models.DateTimeField()
    owner = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(
                fields=["state", "available_at"], name="dispatch_state_available_idx"
            )
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["job", "generation"], name="job_dispatch_generation_unique"
            )
        ]
