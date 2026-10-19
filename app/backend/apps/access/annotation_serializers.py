import json
from typing import ClassVar

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.access.models import Bookmark, Highlight, HighlightColor, HighlightKind
from apps.access.reading.bookmark_positions import normalized_bookmark_position
from apps.catalog.serializers.public import CollectionParametersSerializer

MAX_NOTE_LENGTH = 5000
MAX_SELECTED_TEXT_LENGTH = 5000


class PersonalAnnotationParametersSerializer(CollectionParametersSerializer):
    include_counts = serializers.BooleanField(default=False)
    book = serializers.CharField(max_length=255, required=False, allow_blank=True)
    view = serializers.ChoiceField(
        choices=["all", "highlights", "notes", "quotes"], default="all"
    )
    color = serializers.ChoiceField(
        choices=HighlightColor.choices, allow_blank=True, default=""
    )


class TextSelectionSerializer(serializers.Serializer):
    start = serializers.IntegerField(min_value=0, max_value=32_000_000)
    end = serializers.IntegerField(min_value=1, max_value=32_000_000)

    def validate(self, values):
        if values["end"] <= values["start"]:
            raise serializers.ValidationError("Selection end must follow its start.")
        return values


class BookmarkCreateSerializer(serializers.Serializer):
    location = serializers.CharField(max_length=255)
    chapter_href = serializers.CharField(max_length=512)
    chapter_label = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    note = serializers.CharField(
        max_length=MAX_NOTE_LENGTH, required=False, allow_blank=True
    )
    preview_text = serializers.CharField(
        max_length=280, required=False, allow_blank=True
    )

    def validate_location(self, value):
        return normalized_bookmark_position(value)


class HighlightCreateSerializer(serializers.Serializer):
    chapter_href = serializers.CharField(max_length=512)
    chapter_label = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    selector = TextSelectionSerializer()
    text = serializers.CharField(max_length=MAX_SELECTED_TEXT_LENGTH)
    note = serializers.CharField(
        max_length=MAX_NOTE_LENGTH, required=False, allow_blank=True
    )
    color = serializers.ChoiceField(
        choices=HighlightColor.choices, default=HighlightColor.YELLOW
    )
    kind = serializers.ChoiceField(
        choices=HighlightKind.choices, default=HighlightKind.HIGHLIGHT
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=80), max_length=10, required=False
    )


class BookmarkDetailSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_slug = serializers.CharField(source="book.slug", read_only=True)

    class Meta:
        model = Bookmark
        fields: ClassVar = (
            "id",
            "book_title",
            "book_slug",
            "location",
            "label",
            "note",
            "chapter_href",
            "chapter_label",
            "preview_text",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class HighlightDetailSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    selector = serializers.SerializerMethodField()
    legacy_cfi = serializers.SerializerMethodField()
    tags = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Highlight
        fields: ClassVar = (
            "id",
            "book_title",
            "book_slug",
            "selector",
            "legacy_cfi",
            "text",
            "note",
            "chapter_href",
            "chapter_label",
            "color",
            "kind",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    @extend_schema_field(TextSelectionSerializer(allow_null=True))
    def get_selector(self, annotation):
        try:
            payload = json.loads(annotation.cfi_range)
        except (ValueError, TypeError):
            return None
        selector = TextSelectionSerializer(data=payload)
        return selector.validated_data if selector.is_valid() else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_legacy_cfi(self, annotation):
        value = annotation.cfi_range
        return (
            value
            if value.startswith("epubcfi(")
            and value.endswith(")")
            and len(value) <= 1024
            else None
        )


class BookmarkCollectionSerializer(serializers.Serializer):
    entries = BookmarkDetailSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()


class HighlightCollectionSerializer(serializers.Serializer):
    entries = HighlightDetailSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()


class AnnotationUpdateSerializer(serializers.Serializer):
    color = serializers.ChoiceField(choices=HighlightColor.choices, required=False)
    kind = serializers.ChoiceField(choices=HighlightKind.choices, required=False)
    expected_updated_at = serializers.DateTimeField()
    note = serializers.CharField(max_length=MAX_NOTE_LENGTH, allow_blank=True)


class AnnotationSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    book_title = serializers.CharField(source="book.title")
    book_slug = serializers.CharField(source="book.slug")
    chapter_label = serializers.CharField()
    note_preview = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class BookmarkSummarySerializer(AnnotationSummarySerializer):
    preview_text = serializers.CharField()


class HighlightSummarySerializer(AnnotationSummarySerializer):
    text_preview = serializers.CharField()
    color = serializers.ChoiceField(choices=HighlightColor.choices)
    kind = serializers.ChoiceField(choices=HighlightKind.choices)


class AnnotationCountsSerializer(serializers.Serializer):
    highlights = serializers.IntegerField()
    notes = serializers.IntegerField()
    quotes = serializers.IntegerField()
    bookmarks = serializers.IntegerField()


class PersonalBookmarksSerializer(serializers.Serializer):
    counts = AnnotationCountsSerializer(required=False)
    entries = BookmarkSummarySerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()


class PersonalHighlightsSerializer(serializers.Serializer):
    counts = AnnotationCountsSerializer(required=False)
    entries = HighlightSummarySerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
