from datetime import time

from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel

from .choices import (
    CatalogAutomationFrequency,
    CatalogCurationMode,
    CatalogCurationTrigger,
    JobStatus,
    SourceCatalogRefreshStatus,
)


class SourceCatalogEntry(UUIDPrimaryKeyModel, TimeStampedModel):
    source_url = models.URLField(max_length=1000, unique=True)
    title = models.CharField(max_length=255)
    author_line = models.CharField(max_length=255, blank=True)
    normalized_title = models.CharField(max_length=255, db_index=True)
    normalized_display = models.CharField(max_length=255, db_index=True)
    raw_data = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]


class CatalogAutomationSettings(UUIDPrimaryKeyModel, TimeStampedModel):
    singleton_key = models.CharField(max_length=32, unique=True, default="default")
    enabled = models.BooleanField(default=False)
    daily_run_time = models.TimeField(default=time(2, 0))
    frequency = models.CharField(
        max_length=24,
        choices=CatalogAutomationFrequency.choices,
        default=CatalogAutomationFrequency.DAILY,
    )
    mode = models.CharField(max_length=16, choices=CatalogCurationMode.choices, default=CatalogCurationMode.PENDING)
    refresh_max_pages = models.PositiveIntegerField(default=80)
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="catalog_automation_updates",
    )

    class Meta:
        ordering = ["singleton_key"]


class SourceCatalogRefreshState(UUIDPrimaryKeyModel, TimeStampedModel):
    singleton_key = models.CharField(max_length=32, unique=True, default="default")
    status = models.CharField(
        max_length=16,
        choices=SourceCatalogRefreshStatus.choices,
        default=SourceCatalogRefreshStatus.IDLE,
    )
    max_pages = models.PositiveIntegerField(default=80)
    task_id = models.CharField(max_length=255, blank=True)
    queue_name = models.CharField(max_length=100, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    refreshed_entries = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="source_catalog_refreshes",
    )
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["singleton_key"]


class CatalogCurationRun(UUIDPrimaryKeyModel, TimeStampedModel):
    trigger = models.CharField(max_length=16, choices=CatalogCurationTrigger.choices, default=CatalogCurationTrigger.MANUAL)
    mode = models.CharField(max_length=16, choices=CatalogCurationMode.choices, default=CatalogCurationMode.PENDING)
    status = models.CharField(max_length=16, choices=JobStatus.choices, default=JobStatus.QUEUED)
    refresh_catalog = models.BooleanField(default=True)
    refresh_max_pages = models.PositiveIntegerField(default=80)
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="catalog_curation_runs",
    )
    task_id = models.CharField(max_length=255, blank=True)
    queue_name = models.CharField(max_length=100, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    cancel_requested = models.BooleanField(default=False)
    summary = models.JSONField(default=dict, blank=True)
    last_error = models.TextField(blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]


__all__ = [
    "CatalogAutomationSettings",
    "CatalogCurationRun",
    "SourceCatalogEntry",
    "SourceCatalogRefreshState",
]
