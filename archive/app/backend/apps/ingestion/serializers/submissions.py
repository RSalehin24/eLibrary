from rest_framework import serializers

from apps.catalog.serializers import BookListSerializer
from apps.ingestion.models import BookSubmission, MatchCandidate, ProcessingJob

from .common import present_status


class MatchCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchCandidate
        fields = ["id", "rank", "candidate_title", "candidate_author", "candidate_url", "confidence", "is_selected"]


class ProcessingJobSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    submission_id = serializers.UUIDField(source="submission.id", read_only=True)
    submission_input = serializers.CharField(source="submission.original_input", read_only=True)
    submission_origin = serializers.CharField(source="submission.origin", read_only=True)
    submission_status = serializers.SerializerMethodField()
    submission_resolution_status = serializers.CharField(source="submission.resolution_status", read_only=True)
    target_book_slug = serializers.SerializerMethodField()
    target_book_title = serializers.SerializerMethodField()
    target_book_deleted = serializers.SerializerMethodField()
    class Meta:
        model = ProcessingJob
        fields = [
            "id",
            "submission_id",
            "job_type",
            "status",
            "task_id",
            "queue_name",
            "retry_count",
            "cancel_requested",
            "submission_origin",
            "submission_input",
            "submission_status",
            "submission_resolution_status",
            "target_book_slug",
            "target_book_title",
            "target_book_deleted",
            "last_error",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        ]

    def linked_book_for(self, submission):
        return submission.linked_book if submission.linked_book_id else None

    def get_target_book(self, obj):
        if obj.book_id and not obj.book.deleted_at:
            return obj.book
        linked_book = self.linked_book_for(obj.submission)
        return linked_book if linked_book and not linked_book.deleted_at else None

    def get_raw_target_book(self, obj):
        return obj.book if obj.book_id else self.linked_book_for(obj.submission)

    def get_target_book_slug(self, obj):
        book = self.get_target_book(obj)
        return book.slug if book else ""

    def get_target_book_title(self, obj):
        book = self.get_raw_target_book(obj)
        return book.title if book else ""

    def get_status(self, obj):
        return present_status(obj.status)

    def get_submission_status(self, obj):
        return present_status(obj.submission.status)

    def get_target_book_deleted(self, obj):
        book = self.get_raw_target_book(obj)
        return bool(book and book.deleted_at)


class ProcessingBookSummarySerializer(BookListSerializer):
    class Meta(BookListSerializer.Meta):
        fields = ["id", "title", "slug", "authors", "series"]


class SubmissionSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    candidates = serializers.SerializerMethodField()
    latest_job = serializers.SerializerMethodField()
    linked_book_slug = serializers.SerializerMethodField()
    linked_book = serializers.SerializerMethodField()
    linked_book_deleted = serializers.SerializerMethodField()
    served_from_database = serializers.SerializerMethodField()
    canonical_submission_id = serializers.SerializerMethodField()
    uses_existing_request = serializers.SerializerMethodField()

    class Meta:
        model = BookSubmission
        fields = [
            "id",
            "input_type",
            "origin",
            "original_input",
            "resolved_url",
            "resolution_status",
            "resolution_confidence",
            "status",
            "review_state",
            "error_message",
            "linked_book_slug",
            "linked_book",
            "linked_book_deleted",
            "served_from_database",
            "canonical_submission_id",
            "uses_existing_request",
            "candidates",
            "latest_job",
            "created_at",
            "updated_at",
        ]

    def linked_book_for(self, obj):
        return obj.linked_book if obj.linked_book_id else None

    def get_status(self, obj):
        linked_book = self.linked_book_for(obj)
        if linked_book and linked_book.deleted_at:
            return "deleted"
        return present_status(obj.status)

    def get_candidates(self, obj):
        attempt = obj.resolution_attempts.first() or (obj.canonical_submission.resolution_attempts.first() if obj.canonical_submission_id else None)
        return MatchCandidateSerializer(attempt.match_candidates.all()[:3], many=True).data if attempt else []

    def get_latest_job(self, obj):
        job = obj.processing_jobs.first() or (obj.canonical_submission.processing_jobs.first() if obj.canonical_submission_id else None)
        return ProcessingJobSerializer(job).data if job else None

    def get_linked_book_slug(self, obj):
        linked_book = self.linked_book_for(obj)
        return linked_book.slug if linked_book and not linked_book.deleted_at else ""

    def get_linked_book(self, obj):
        linked_book = self.linked_book_for(obj)
        return (
            ProcessingBookSummarySerializer(linked_book, context=self.context).data
            if linked_book
            else None
        )

    def get_linked_book_deleted(self, obj):
        linked_book = self.linked_book_for(obj)
        return bool(linked_book and linked_book.deleted_at)

    def get_served_from_database(self, obj):
        return bool(obj.raw_payload.get("served_from_database"))

    def get_canonical_submission_id(self, obj):
        return str(obj.canonical_submission.id) if obj.canonical_submission else ""

    def get_uses_existing_request(self, obj):
        return bool(obj.canonical_submission_id)

__all__ = [
    "MatchCandidateSerializer",
    "ProcessingBookSummarySerializer",
    "ProcessingJobSerializer",
    "SubmissionSerializer",
]
