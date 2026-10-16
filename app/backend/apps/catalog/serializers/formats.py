from rest_framework import serializers

from apps.catalog.models import ManualBindingType

BOOK_FORMAT_FIELDS = (
    "edition",
    "manual_language",
    "manual_publisher",
    "manual_price",
    "manual_binding",
    "manual_is_compilation",
)


class BookFormatSerializer(serializers.Serializer):
    edition = serializers.CharField(max_length=120, allow_blank=True, required=False)
    manual_language = serializers.RegexField(
        r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
        max_length=16,
        allow_blank=True,
        required=False,
    )
    manual_publisher = serializers.CharField(
        max_length=255, allow_blank=True, required=False
    )
    manual_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        allow_null=True,
        required=False,
    )
    manual_binding = serializers.ChoiceField(
        choices=ManualBindingType.choices,
        allow_blank=True,
        required=False,
    )
    manual_is_compilation = serializers.BooleanField(required=False)
