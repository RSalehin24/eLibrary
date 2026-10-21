from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.discovery.cursors import discovery_page
from apps.catalog.discovery.queries import (
    PUBLIC_BOOK_FIELDS,
    discovery_queryset,
    published_books,
    with_public_relations,
)
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.serializers.editorial import EDITORIAL_DETAIL_FIELDS
from apps.catalog.serializers.public import (
    DiscoveryParametersSerializer,
    PublicBookCollectionSerializer,
    PublicBookDetailSerializer,
    PublicBookListSerializer,
)
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.collection_pagination import collection_pagination, counted_collection


class PublicBookListView(VersionedAPIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_books_list",
        parameters=[DiscoveryParametersSerializer],
        responses={200: PublicBookCollectionSerializer, 400: APIErrorSerializer},
    )
    def get(self, request):
        parameters = DiscoveryParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        if (
            parameters.validated_data["ownership"]
            or parameters.validated_data["sort"].lstrip("-") == "requested_at"
        ):
            parameters.validated_data["scope"] = f"public:{request.user.pk}"
        queryset = counted_collection(
            discovery_queryset(parameters.validated_data, request.user)
        )
        entries, next_cursor = discovery_page(queryset, parameters.validated_data)
        return Response(
            {
                "entries": PublicBookListSerializer(entries, many=True).data,
                "next_cursor": next_cursor,
                "has_more": next_cursor is not None,
                "pagination": collection_pagination(
                    queryset, parameters.validated_data, entries
                ),
            }
        )


class PublicBookDetailView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_book_detail",
        responses={200: PublicBookDetailSerializer, 404: APIErrorSerializer},
    )
    def get(self, request, slug):
        queryset = with_public_relations(
            published_books().only(
                *PUBLIC_BOOK_FIELDS,
                "summary",
                "record_type",
                "manual_publisher",
                "manual_price",
                "manual_binding",
                "manual_is_compilation",
                *EDITORIAL_DETAIL_FIELDS,
            )
        )
        book = catalog_object_by_slug(queryset, slug)
        return Response(PublicBookDetailSerializer(book).data)
