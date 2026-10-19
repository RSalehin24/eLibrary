from rest_framework import serializers

from apps.access.reader_serializers import ReaderLabelSerializer


class BookFrontMatterSerializer(ReaderLabelSerializer):
    value = serializers.CharField()


class BookContentsEntrySerializer(ReaderLabelSerializer):
    depth = serializers.IntegerField(min_value=0, max_value=8)


class BookDetailPreviewSerializer(serializers.Serializer):
    front_matter = BookFrontMatterSerializer(many=True)
    front_matter_text = serializers.CharField(allow_blank=True)
    dedication = serializers.CharField(allow_blank=True)
    contents = BookContentsEntrySerializer(many=True)
    truncated = serializers.BooleanField()
