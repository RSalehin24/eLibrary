from rest_framework import serializers

from apps.catalog.models import Contributor
from apps.catalog.serializers.editorial import (
    PUBLIC_EDITORIAL_FIELDS,
    PublicEditorialSerializer,
)
from apps.common.collection_pagination import CollectionPaginationSerializer


class PublicEntityListSerializer(serializers.ModelSerializer):
    book_count = serializers.IntegerField(read_only=True, required=False)
    catalog_code = serializers.SerializerMethodField()

    def get_catalog_code(self, entity) -> str | None:
        return getattr(entity, "catalog_code", None)

    class Meta:
        model = Contributor
        fields = ("id", "name", "slug", "book_count", "catalog_code", "created_at")
        read_only_fields = fields


class PublicEntityCollectionSerializer(serializers.Serializer):
    entries = PublicEntityListSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
    pagination = CollectionPaginationSerializer()


class PublicEntityDetailSerializer(PublicEditorialSerializer):
    class Meta:
        model = Contributor
        fields = ("id", "name", "slug", *PUBLIC_EDITORIAL_FIELDS)
        read_only_fields = fields
