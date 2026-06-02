from django.db import models

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel

from .choices import DuplicateReviewStatus, JobStatus, JobType
from .submissions import BookSubmission


class ProcessingJob(UUIDPrimaryKeyModel, TimeStampedModel):
    submission = models.ForeignKey(BookSubmission, on_delete=models.CASCADE, related_name="processing_jobs")
    book = models.ForeignKey("catalog.Book", on_delete=models.SET_NULL, blank=True, null=True, related_name="processing_jobs")
    job_type = models.CharField(max_length=24, choices=JobType.choices, default=JobType.INGESTION, db_index=True)
    status = models.CharField(max_length=16, choices=JobStatus.choices, default=JobStatus.QUEUED, db_index=True)
    task_id = models.CharField(max_length=255, blank=True)
    queue_name = models.CharField(max_length=100, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    cancel_requested = models.BooleanField(default=False)
    payload = models.JSONField(default=dict, blank=True)
    last_error = models.TextField(blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]


class ProcessingLog(UUIDPrimaryKeyModel, TimeStampedModel):
    job = models.ForeignKey(ProcessingJob, on_delete=models.CASCADE, related_name="logs")
    level = models.CharField(max_length=16, default="info")
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]


class DuplicateReview(UUIDPrimaryKeyModel, TimeStampedModel):
    submission = models.ForeignKey(BookSubmission, on_delete=models.CASCADE, related_name="duplicate_reviews")
    existing_book = models.ForeignKey("catalog.Book", on_delete=models.CASCADE, related_name="duplicate_reviews")
    detected_by = models.CharField(max_length=50, default="exact_source_url")
    status = models.CharField(max_length=24, choices=DuplicateReviewStatus.choices, default=DuplicateReviewStatus.PENDING)
    notes = models.TextField(blank=True)
    raw_evidence = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


__all__ = ["DuplicateReview", "ProcessingJob", "ProcessingLog"]
