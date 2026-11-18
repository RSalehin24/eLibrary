from django.db import models

from apps.common.models import ReviewState, TimeStampedModel, UUIDPrimaryKeyModel

from .choices import ResolutionStatus, SubmissionInputType, SubmissionOrigin, SubmissionStatus


class BookSubmission(UUIDPrimaryKeyModel, TimeStampedModel):
    submitter = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, blank=True, null=True, related_name="submissions")
    input_type = models.CharField(max_length=16, choices=SubmissionInputType.choices)
    origin = models.CharField(max_length=16, choices=SubmissionOrigin.choices, default=SubmissionOrigin.USER, db_index=True)
    original_input = models.TextField()
    normalized_input = models.TextField(blank=True)
    resolved_url = models.URLField(max_length=1000, blank=True)
    resolution_status = models.CharField(max_length=24, choices=ResolutionStatus.choices, default=ResolutionStatus.UNRESOLVED)
    resolution_confidence = models.FloatField(default=0.0)
    status = models.CharField(max_length=32, choices=SubmissionStatus.choices, default=SubmissionStatus.DRAFT, db_index=True)
    review_state = models.CharField(max_length=32, choices=ReviewState.choices, default=ReviewState.PENDING)
    linked_book = models.ForeignKey("catalog.Book", on_delete=models.SET_NULL, blank=True, null=True, related_name="linked_submissions")
    duplicate_of_book = models.ForeignKey("catalog.Book", on_delete=models.SET_NULL, blank=True, null=True, related_name="duplicate_submissions")
    canonical_submission = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True, related_name="deduplicated_submissions")
    raw_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        previous = {"linked_book_id": None, "submitter_id": None}
        if self.pk:
            previous = (
                BookSubmission.objects.filter(pk=self.pk)
                .values("linked_book_id", "submitter_id")
                .first()
                or previous
            )
        super().save(*args, **kwargs)
        if self.submitter_id and self.linked_book_id and (
            previous["linked_book_id"] != self.linked_book_id
            or previous["submitter_id"] != self.submitter_id
        ):
            from apps.catalog.models import UserBook

            UserBook.objects.get_or_create(user_id=self.submitter_id, book_id=self.linked_book_id)


class TitleResolutionAttempt(UUIDPrimaryKeyModel, TimeStampedModel):
    submission = models.ForeignKey(BookSubmission, on_delete=models.CASCADE, related_name="resolution_attempts")
    query = models.TextField()
    normalized_query = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=ResolutionStatus.choices, default=ResolutionStatus.UNRESOLVED)
    confidence = models.FloatField(default=0.0)
    resolved_url = models.URLField(max_length=1000, blank=True)
    raw_results = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class MatchCandidate(UUIDPrimaryKeyModel, TimeStampedModel):
    resolution_attempt = models.ForeignKey(TitleResolutionAttempt, on_delete=models.CASCADE, related_name="match_candidates")
    rank = models.PositiveIntegerField(default=0)
    candidate_title = models.CharField(max_length=255)
    candidate_author = models.CharField(max_length=255, blank=True)
    candidate_url = models.URLField(max_length=1000)
    confidence = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)
    is_selected = models.BooleanField(default=False)

    class Meta:
        ordering = ["rank"]


__all__ = ["BookSubmission", "MatchCandidate", "TitleResolutionAttempt"]
