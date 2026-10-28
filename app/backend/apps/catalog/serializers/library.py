from rest_framework import serializers

from apps.catalog.discovery.personal import personal_feed
from apps.catalog.serializers.public import (
    DiscoveryParametersSerializer,
    PublicBookDetailSerializer,
    PublicBookListSerializer,
)
from apps.common.collection_pagination import CollectionPaginationSerializer


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
            "progress_percent",
            "last_location",
            "activity_at",
        )
        read_only_fields = fields


class LibraryCollectionSerializer(serializers.Serializer):
    entries = LibraryBookSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
    pagination = CollectionPaginationSerializer()


class PersonalBookDetailSerializer(PublicBookDetailSerializer):
    library_view = serializers.SerializerMethodField()

    def get_library_view(self, book) -> str:
        actor = self.context["request"].user
        return (
            "all"
            if personal_feed(actor, "all").filter(pk=book.pk).exists()
            else "granted"
        )

    class Meta(PublicBookDetailSerializer.Meta):
        fields = (*PublicBookDetailSerializer.Meta.fields, "library_view")
        read_only_fields = fields
