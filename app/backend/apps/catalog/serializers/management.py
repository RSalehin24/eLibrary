from rest_framework import serializers

from apps.catalog.models import ManualBindingType
from apps.catalog.serializers.editorial import (
    EDITORIAL_DETAIL_FIELDS,
    VerifiedAlternativeNamesField,
)
from apps.catalog.serializers.formats import BOOK_FORMAT_FIELDS
from apps.catalog.serializers.public import AdminBookListSerializer


class ManagedBookDetailSerializer(AdminBookListSerializer):
    alternative_names = VerifiedAlternativeNamesField(read_only=True)
    manual_binding = serializers.ChoiceField(
        choices=ManualBindingType.choices,
        allow_blank=True,
        read_only=True,
    )

    class Meta(AdminBookListSerializer.Meta):
        fields = (
            *AdminBookListSerializer.Meta.fields,
            "summary",
            *BOOK_FORMAT_FIELDS[1:],
            *EDITORIAL_DETAIL_FIELDS,
            "updated_at",
        )
        read_only_fields = fields
