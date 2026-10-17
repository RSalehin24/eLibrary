from typing import ClassVar

from rest_framework import serializers

from apps.catalog.models import Book
from apps.catalog.models.editorial import validate_alternative_names
from apps.catalog.serializers.formats import BOOK_FORMAT_FIELDS, BookFormatSerializer
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.common.validation import reject_unknown_fields

EDITORIAL_FIELDS = (
    "editorial_description",
    "alternative_names",
    "seo_title",
    "seo_description",
    "social_image_url",
    "indexing_eligible",
)
EDITORIAL_DETAIL_FIELDS = (*EDITORIAL_FIELDS, "editorial_reviewed_at")
PUBLIC_EDITORIAL_FIELDS = (*EDITORIAL_FIELDS[:-1], "indexable")


class VerifiedAlternativeNamesField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(
            child=serializers.CharField(max_length=255),
            max_length=20,
            validators=[validate_alternative_names],
            **kwargs,
        )


class ReviewedEditorialSerializer(serializers.ModelSerializer):
    indexable = serializers.BooleanField(source="is_indexable", read_only=True)
    alternative_names = VerifiedAlternativeNamesField(read_only=True)


class ExpectedRevisionSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()


class BookEditorialUpdateSerializer(BookFormatSerializer, serializers.ModelSerializer):
    expected_updated_at = serializers.DateTimeField()
    alternative_names = VerifiedAlternativeNamesField(required=False)
    editorial_description = serializers.CharField(
        max_length=20000, allow_blank=True, required=False
    )
    summary = serializers.CharField(max_length=20000, allow_blank=True, required=False)

    class Meta:
        model = Book
        fields = (
            "expected_updated_at",
            "title",
            "summary",
            *EDITORIAL_FIELDS,
            *BOOK_FORMAT_FIELDS,
        )
        extra_kwargs: ClassVar = {
            "title": {"required": False},
            "indexing_eligible": {"required": False},
        }

    def validate_title(self, value):
        title = clean_display_text(value)
        if not normalize_catalog_text(title):
            raise serializers.ValidationError(
                "A title must contain letters or numbers."
            )
        return title

    def validate(self, attributes):
        reject_unknown_fields(self)
        if len(attributes) == 1:
            raise serializers.ValidationError(
                {"non_field_errors": "Supply metadata to update."}
            )
        return attributes
