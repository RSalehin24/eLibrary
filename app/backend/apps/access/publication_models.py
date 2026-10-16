from typing import ClassVar

from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel


class PreparationState(models.TextChoices):
    PENDING = "pending", "Pending"
    PREPARING = "preparing", "Preparing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class PreparedPublication(UUIDPrimaryKeyModel, TimeStampedModel):
    checksum = models.CharField(max_length=64, unique=True)
    state = models.CharField(
        max_length=16,
        choices=PreparationState.choices,
        default=PreparationState.PENDING,
    )
    manifest = models.JSONField(default=dict)
    storage_reference = models.CharField(max_length=64, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    error = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at"]
