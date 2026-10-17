from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.discovery.cursors import discovery_page
from apps.catalog.discovery.entity_directory import directory_queryset
from apps.catalog.serializers.entities import (
    PublicEntityCollectionSerializer,
    PublicEntityListSerializer,
)
from apps.catalog.serializers.public import CollectionParametersSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


def collection_queryset(query):
    return directory_queryset("collections", {"q": query})


class PublicCollectionsView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_collections_list",
        parameters=[CollectionParametersSerializer],
        responses={200: PublicEntityCollectionSerializer, 400: APIErrorSerializer},
    )
    def get(self, request):
        parameters = CollectionParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        parameters.validated_data["scope"] = "collections"
        entries, cursor = discovery_page(
            collection_queryset(parameters.validated_data["q"]),
            parameters.validated_data,
        )
        return Response(
            {
                "entries": PublicEntityListSerializer(entries, many=True).data,
                "next_cursor": cursor,
                "has_more": cursor is not None,
            }
        )
