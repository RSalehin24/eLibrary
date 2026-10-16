from typing import ClassVar

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel
from apps.ingestion.models import CatalogAutomationFrequency


class SourceAutomation(UUIDPrimaryKeyModel, TimeStampedModel):
    name = models.CharField(max_length=150)
    enabled = models.BooleanField(default=False)
    frequency = models.CharField(
        max_length=24,
        choices=CatalogAutomationFrequency.choices,
        default=CatalogAutomationFrequency.DAILY,
    )
    first_run_at = models.DateTimeField()
    time_zone = models.CharField(
        max_length=64, default=timezone.get_default_timezone_name
    )
    next_run_at = models.DateTimeField()
    occurrence_number = models.PositiveIntegerField(default=0)
    source_max_pages = models.PositiveSmallIntegerField(default=20)
    processing_limit = models.PositiveSmallIntegerField(default=0)
    run_as = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="source_automations",
    )

    class Meta:
        ordering: ClassVar[list[str]] = ["name", "id"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["enabled", "next_run_at"], name="automation_due_idx")
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=models.Q(
                    source_max_pages__gte=1,
                    source_max_pages__lte=200,
                    processing_limit__gte=0,
                    processing_limit__lte=100,
                ),
                name="automation_bounded_work",
            )
        ]


class AutomationRun(UUIDPrimaryKeyModel, TimeStampedModel):
    automation = models.ForeignKey(
        SourceAutomation, on_delete=models.PROTECT, related_name="runs"
    )
    due_at = models.DateTimeField()
    state = models.CharField(
        max_length=16, choices=[("queued", "Queued"), ("blocked", "Blocked")]
    )
    error_code = models.CharField(max_length=64, blank=True)
    job = models.OneToOneField(
        "processing.BackgroundJob",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="automation_execution",
    )
    processing_limit = models.PositiveSmallIntegerField(default=0)
    missed_occurrences = models.PositiveIntegerField(default=0)

    class Meta:
        ordering: ClassVar[list[str]] = ["-due_at", "-id"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["automation", "due_at"], name="automation_occurrence_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(state="queued", job__isnull=False)
                | models.Q(state="blocked", job__isnull=True),
                name="automation_run_valid_state",
            ),
        ]
