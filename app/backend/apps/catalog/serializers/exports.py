from rest_framework import serializers

from apps.catalog.serializers.library import LibraryParametersSerializer
from apps.catalog.serializers.public import (
    CatalogFilterParametersSerializer,
)


class CatalogExportParametersSerializer(CatalogFilterParametersSerializer):
    page = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False)
    export_format = serializers.ChoiceField(
        choices=["csv", "pdf", "print"], default="csv"
    )


class LibraryExportParametersSerializer(LibraryParametersSerializer):
    export_format = serializers.ChoiceField(
        choices=["csv", "pdf", "print"], default="csv"
    )
