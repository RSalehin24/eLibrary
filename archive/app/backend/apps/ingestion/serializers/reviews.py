from rest_framework import serializers

from apps.ingestion.models import DuplicateReview, ProcessingLog

from .submissions import ProcessingBookSummarySerializer, SubmissionSerializer


class DuplicateReviewSerializer(serializers.ModelSerializer):
    submission = SubmissionSerializer(read_only=True)
    existing_book = ProcessingBookSummarySerializer(read_only=True)
    existing_book_deleted = serializers.SerializerMethodField()

    class Meta:
        model = DuplicateReview
        fields = [
            "id",
            "detected_by",
            "status",
            "notes",
            "raw_evidence",
            "submission",
            "existing_book",
            "existing_book_deleted",
            "created_at",
        ]

    def get_existing_book_deleted(self, obj):
        return bool(obj.existing_book_id and obj.existing_book.deleted_at)


class ProcessingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingLog
        fields = ["id", "level", "message", "details", "created_at"]


class DuplicateReviewDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=["same_book", "new_book", "confirm_existing", "dismiss"],
    )
    notes = serializers.CharField(required=False, allow_blank=True)


__all__ = [
    "DuplicateReviewDecisionSerializer",
    "DuplicateReviewSerializer",
    "ProcessingLogSerializer",
]
