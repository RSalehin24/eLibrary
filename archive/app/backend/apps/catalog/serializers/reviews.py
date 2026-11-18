from rest_framework import serializers

from apps.catalog.models import MetadataReview


class MetadataReviewSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)
    reviewer_email = serializers.EmailField(source="reviewer.email", read_only=True)

    class Meta:
        model = MetadataReview
        fields = [
            "id",
            "state",
            "notes",
            "requested_by",
            "requested_by_email",
            "reviewer",
            "reviewer_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["requested_by", "reviewer", "created_at", "updated_at"]


class MetadataReviewDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetadataReview
        fields = ["state", "notes"]
