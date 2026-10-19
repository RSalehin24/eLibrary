from rest_framework import serializers

from apps.catalog.models import Contributor
from apps.catalog.serializers.editorial import (
    PUBLIC_EDITORIAL_FIELDS,
    ReviewedEditorialSerializer,
)


class PublicEntityListSerializer(serializers.ModelSerializer):
    book_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Contributor
        fields = ("id", "name", "slug", "book_count")
        read_only_fields = fields


class PublicEntityCollectionSerializer(serializers.Serializer):
    entries = PublicEntityListSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()


class PublicEntityDetailSerializer(ReviewedEditorialSerializer):
    class Meta:
        model = Contributor
        fields = ("id", "name", "slug", *PUBLIC_EDITORIAL_FIELDS)
        read_only_fields = fields
