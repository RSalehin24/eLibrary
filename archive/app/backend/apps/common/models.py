import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class UUIDPrimaryKeyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class LifecycleState(models.TextChoices):
    DRAFT = "draft", "Draft"
    PROCESSING = "processing", "Processing"
    NEEDS_REVIEW = "needs_review", "Needs review"
    READY = "ready", "Ready"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"
    SOFT_DELETED = "soft_deleted", "Soft deleted"


class ReviewState(models.TextChoices):
    PENDING = "pending", "Pending"
    NEEDS_REVIEW = "needs_review", "Needs review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class AuditLog(UUIDPrimaryKeyModel, TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="audit_events",
    )
    verb = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    request_id = models.CharField(max_length=100, blank=True)
    remote_addr = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.verb} {self.target_type}:{self.target_id}"


class SavedFilterTarget(models.TextChoices):
    CATALOG = "catalog", "Catalog"
    QUEUE = "queue", "Queue"


class SavedFilter(UUIDPrimaryKeyModel, TimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_filters",
    )
    target = models.CharField(max_length=32, choices=SavedFilterTarget.choices)
    name = models.CharField(max_length=120)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["target", "name"]
        unique_together = ("owner", "target", "name")

    def __str__(self):
        return f"{self.owner} / {self.target} / {self.name}"
