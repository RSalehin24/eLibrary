import math

from rest_framework import serializers


class ReaderLabelSerializer(serializers.Serializer):
    def get_fields(self):
        fields = super().get_fields()
        fields["label"] = serializers.CharField()
        return fields


class ReaderChapterSerializer(ReaderLabelSerializer):
    path = serializers.CharField()
    spine_index = serializers.IntegerField(required=False)
    idref = serializers.CharField(required=False)
    spine_step = serializers.IntegerField(required=False)
    href = serializers.CharField(required=False)


class ReaderProgressSerializer(serializers.Serializer):
    last_location = serializers.CharField(max_length=255, allow_blank=True)
    progress_percent = serializers.FloatField(min_value=0, max_value=100)

    def validate_progress_percent(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Progress must be a finite percentage.")
        return value


class ReaderNavigationSerializer(ReaderLabelSerializer):
    chapter_index = serializers.IntegerField(allow_null=True)
    fragment = serializers.CharField(allow_blank=True)
    depth = serializers.IntegerField(min_value=0, max_value=8)


class ReaderSessionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    book_title = serializers.CharField(source="book.title")
    book_slug = serializers.CharField(source="book.slug")
    expires_at = serializers.DateTimeField()
    chapters = serializers.ListField(child=ReaderChapterSerializer())
    navigation = serializers.ListField(
        child=ReaderNavigationSerializer(), required=False
    )
    resource_base = serializers.CharField()
    reading_progress = ReaderProgressSerializer()
    progress_matches_edition = serializers.BooleanField()


class ReaderAccessSerializer(serializers.Serializer):
    cover_url = serializers.CharField(allow_null=True)
    html_url = serializers.CharField(allow_null=True)
    can_read = serializers.BooleanField()
    can_download = serializers.BooleanField()
    can_send_kindle = serializers.BooleanField()
    prepared = serializers.BooleanField()
    active_session_id = serializers.UUIDField(allow_null=True)
    progress_session_id = serializers.UUIDField(allow_null=True)
    reading_progress = ReaderProgressSerializer(allow_null=True)
    last_opened_at = serializers.DateTimeField(allow_null=True)
