from rest_framework import serializers

from apps.catalog.serializers.public import (
    DiscoveryParametersSerializer,
    PublicBookListSerializer,
)


class LibraryParametersSerializer(DiscoveryParametersSerializer):
    view = serializers.ChoiceField(
        choices=["all", "owned", "saved", "recent", "granted"], default="all"
    )


class LibraryBookSerializer(PublicBookListSerializer):
    progress_percent = serializers.FloatField(read_only=True, allow_null=True)
    last_location = serializers.CharField(read_only=True, allow_null=True)
    activity_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta(PublicBookListSerializer.Meta):
        fields = (
            *PublicBookListSerializer.Meta.fields,
            "state",
            "review_state",
            "progress_percent",
            "last_location",
            "activity_at",
            "record_type",
        )
        read_only_fields = fields


class LibraryCollectionSerializer(serializers.Serializer):
    entries = LibraryBookSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
