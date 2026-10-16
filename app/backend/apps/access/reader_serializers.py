import math

from rest_framework import serializers


class ReaderChapterSerializer(serializers.Serializer):
    path = serializers.CharField()

    def get_fields(self):
        fields = super().get_fields()
        fields["label"] = serializers.CharField()
        return fields


class ReaderProgressSerializer(serializers.Serializer):
    last_location = serializers.CharField(max_length=255, allow_blank=True)
    progress_percent = serializers.FloatField(min_value=0, max_value=100)

    def validate_progress_percent(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Progress must be a finite percentage.")
        return value


class ReaderSessionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    book_title = serializers.CharField(source="book.title")
    book_slug = serializers.CharField(source="book.slug")
    expires_at = serializers.DateTimeField()
    chapters = serializers.ListField(child=ReaderChapterSerializer())
    resource_base = serializers.CharField()
    reading_progress = ReaderProgressSerializer()


class ReaderAccessSerializer(serializers.Serializer):
    can_read = serializers.BooleanField()
    can_download = serializers.BooleanField()
    can_send_kindle = serializers.BooleanField()
    prepared = serializers.BooleanField()
    active_session_id = serializers.UUIDField(allow_null=True)
