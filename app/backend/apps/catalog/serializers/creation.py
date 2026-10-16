from rest_framework import serializers

from apps.catalog.models import Book, BookRecordType
from apps.catalog.serializers.editorial import BookEditorialUpdateSerializer
from apps.catalog.serializers.formats import BOOK_FORMAT_FIELDS, BookFormatSerializer
from apps.common.validation import reject_unknown_fields


class BookCreateSerializer(BookFormatSerializer, serializers.ModelSerializer):
    operation_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    summary = serializers.CharField(max_length=20000, allow_blank=True, required=False)
    record_type = serializers.ChoiceField(choices=BookRecordType.choices)

    validate_title = BookEditorialUpdateSerializer.validate_title

    class Meta:
        model = Book
        fields = (
            "operation_id",
            "title",
            "summary",
            "record_type",
            *BOOK_FORMAT_FIELDS,
        )

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes
