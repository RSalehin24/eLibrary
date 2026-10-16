from django.db.models import Case, IntegerField, Q, Value, When
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.discovery.cursors import discovery_page
from apps.catalog.discovery.entities import public_entities
from apps.catalog.serializers.entities import (
    PublicEntityCollectionSerializer,
    PublicEntityListSerializer,
)
from apps.catalog.serializers.public import CollectionParametersSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.text import normalize_catalog_text


def collection_queryset(query):
    queryset = public_entities("collections").only("id", "name", "slug", "created_at")
    if not query:
        return queryset.annotate(search_rank=Value(0, output_field=IntegerField()))
    normalized = normalize_catalog_text(query)
    return queryset.filter(
        Q(normalized_name__contains=normalized)
        | Q(normalized_aliases__contains=normalized)
    ).annotate(
        search_rank=Case(
            When(normalized_name=normalized, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    )


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
