from rest_framework import serializers

from apps.accounts.models import User
from apps.catalog.models import MetadataVersion
from apps.common.api_serializers import AdminPaginationSerializer


class MetadataHistoryParametersSerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, max_value=10000, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=10)


class MetadataVersionActorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, actor) -> str:
        return actor.full_name or actor.get_full_name()

    class Meta:
        model = User
        fields = ("id", "name")
        read_only_fields = fields


class MetadataVersionSerializer(serializers.ModelSerializer):
    created_by = MetadataVersionActorSerializer(allow_null=True, read_only=True)

    class Meta:
        model = MetadataVersion
        fields = ("id", "source", "notes", "created_at", "created_by")
        read_only_fields = fields


class MetadataHistoryCollectionSerializer(serializers.Serializer):
    entries = MetadataVersionSerializer(many=True)
    pagination = AdminPaginationSerializer()
