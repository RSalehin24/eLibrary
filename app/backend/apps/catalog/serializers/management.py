from rest_framework import serializers

from apps.catalog.serializers.editorial import (
    EDITORIAL_DETAIL_FIELDS,
    VerifiedAlternativeNamesField,
)
from apps.catalog.serializers.formats import BOOK_FORMAT_FIELDS
from apps.catalog.serializers.public import AdminBookListSerializer


class ManagedBookDetailSerializer(AdminBookListSerializer):
    alternative_names = VerifiedAlternativeNamesField(read_only=True)
    file_metadata_may_differ = serializers.SerializerMethodField()

    def get_file_metadata_may_differ(self, obj) -> bool:
        return bool(obj.metadata_overrides)

    class Meta(AdminBookListSerializer.Meta):
        fields = (
            *AdminBookListSerializer.Meta.fields,
            "summary",
            *BOOK_FORMAT_FIELDS[1:],
            *EDITORIAL_DETAIL_FIELDS,
            "updated_at",
            "file_metadata_may_differ",
        )
        read_only_fields = fields
