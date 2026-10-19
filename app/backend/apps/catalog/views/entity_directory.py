from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.discovery.cursors import cursor_context, discovery_page
from apps.catalog.discovery.directory_counts import (
    DIRECTORY_SORTS,
    DirectorySortPagination,
)
from apps.catalog.discovery.entity_directory import directory_queryset
from apps.catalog.models import ContributorRole
from apps.catalog.serializers.entities import (
    PublicEntityCollectionSerializer,
    PublicEntityListSerializer,
)
from apps.catalog.serializers.public import CollectionParametersSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


class EntityDirectoryParametersSerializer(CollectionParametersSerializer):
    record_type = serializers.ChoiceField(
        choices=["all", "digital", "manual"], default="all"
    )
    sort = serializers.ChoiceField(
        choices=DIRECTORY_SORTS, allow_blank=True, default=""
    )
    role = serializers.ChoiceField(
        choices=ContributorRole.choices, allow_blank=True, default=""
    )


class PublicEntityListView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_entities_list",
        parameters=[
            OpenApiParameter(
                "kind",
                str,
                OpenApiParameter.PATH,
                enum=["contributors", "categories", "series", "collections"],
            ),
            EntityDirectoryParametersSerializer,
        ],
        responses={
            200: PublicEntityCollectionSerializer,
            400: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, kind):
        parameters = EntityDirectoryParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        values = parameters.validated_data
        values["scope"] = f"entities:{kind}:{values['role']}:{values['record_type']}"
        queryset = directory_queryset(kind, values)
        entries, cursor = (
            DirectorySortPagination(values["sort"]).page(
                queryset, values, cursor_context(values)
            )
            if values["sort"]
            else discovery_page(queryset, values)
        )
        return Response(
            {
                "entries": PublicEntityListSerializer(entries, many=True).data,
                "next_cursor": cursor,
                "has_more": cursor is not None,
            }
        )
