from rest_framework import serializers

from apps.catalog.models import PhysicalReadingLog
from apps.common.validation import reject_unknown_fields


class SavedBookSerializer(serializers.Serializer):
    saved = serializers.BooleanField()

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class PhysicalReadingLogSerializer(serializers.ModelSerializer):
    updated_at = serializers.DateTimeField(allow_null=True, read_only=True)

    class Meta:
        model = PhysicalReadingLog
        fields = (
            "status",
            "current_page",
            "total_pages",
            "rating",
            "started_on",
            "finished_on",
            "notes",
            "updated_at",
        )
        read_only_fields = fields


class PhysicalReadingLogUpdateSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField(allow_null=True)
    status = serializers.ChoiceField(choices=["unread", "reading", "finished"])
    current_page = serializers.IntegerField(min_value=0, max_value=1000000)
    total_pages = serializers.IntegerField(
        min_value=1, max_value=1000000, allow_null=True
    )
    rating = serializers.IntegerField(min_value=0, max_value=5)
    started_on = serializers.DateField(allow_null=True)
    finished_on = serializers.DateField(allow_null=True)
    notes = serializers.CharField(max_length=20000, allow_blank=True)

    def validate(self, attributes):
        reject_unknown_fields(self)
        if (
            attributes["total_pages"]
            and attributes["current_page"] > attributes["total_pages"]
        ):
            raise serializers.ValidationError(
                {"current_page": "Progress cannot exceed total pages."}
            )
        if (
            attributes["started_on"]
            and attributes["finished_on"]
            and attributes["started_on"] > attributes["finished_on"]
        ):
            raise serializers.ValidationError(
                {"finished_on": "Finish date cannot precede start date."}
            )
        return attributes
