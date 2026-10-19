from rest_framework import serializers

from apps.catalog.exports.tabular import GROUPS
from apps.catalog.models import ManualBindingType
from apps.catalog.serializers.library import LibraryParametersSerializer
from apps.catalog.serializers.public import (
    CatalogFilterParametersSerializer,
    PublicBookDetailSerializer,
)
from apps.common.api_serializers import AdminPaginationSerializer


class CatalogExportParametersSerializer(CatalogFilterParametersSerializer):
    export_format = serializers.ChoiceField(
        choices=["csv", "pdf", "print"], default="csv"
    )


class LibraryExportParametersSerializer(LibraryParametersSerializer):
    export_format = serializers.ChoiceField(
        choices=["csv", "pdf", "print"], default="csv"
    )


class PhysicalBookParametersSerializer(CatalogFilterParametersSerializer):
    writer = serializers.CharField(max_length=255, allow_blank=True, default="")
    translator = serializers.CharField(max_length=255, allow_blank=True, default="")
    editor = serializers.CharField(max_length=255, allow_blank=True, default="")
    publisher = serializers.CharField(max_length=255, allow_blank=True, default="")
    binding = serializers.ChoiceField(
        choices=["", *ManualBindingType.values], allow_blank=True, default=""
    )
    language = serializers.CharField(max_length=16, allow_blank=True, default="")
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    page = serializers.IntegerField(min_value=1, default=1)


class PhysicalBookExportParametersSerializer(PhysicalBookParametersSerializer):
    export_format = serializers.ChoiceField(
        choices=["csv", "pdf", "xlsx", "print"], default="csv"
    )
    group_by = serializers.ChoiceField(choices=GROUPS, allow_blank=True, default="")


class PhysicalBookCollectionSerializer(serializers.Serializer):
    entries = PublicBookDetailSerializer(many=True)
    pagination = AdminPaginationSerializer()
