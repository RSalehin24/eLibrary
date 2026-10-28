from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.discovery.cursors import cursor_context
from apps.catalog.discovery.library import library_queryset
from apps.catalog.discovery.personal import visible_personal_books
from apps.catalog.discovery.queries import PUBLIC_BOOK_FIELDS, with_public_relations
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.discovery.sorting import CatalogSortPagination
from apps.catalog.serializers.editorial import EDITORIAL_DETAIL_FIELDS
from apps.catalog.serializers.library import (
    LibraryBookSerializer,
    LibraryCollectionSerializer,
    LibraryParametersSerializer,
    PersonalBookDetailSerializer,
)
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.collection_pagination import collection_pagination, counted_collection
from apps.common.ranked_pagination import RankedFeedPagination


class MyBooksView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="my_books_list",
        parameters=[LibraryParametersSerializer],
        responses={
            200: LibraryCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        parameters = LibraryParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        view = parameters.validated_data["view"]
        parameters.validated_data["scope"] = f"library:{request.user.pk}:{view}"
        timestamp = "activity_at" if view == "recent" else "created_at"
        pagination = (
            CatalogSortPagination(parameters.validated_data["sort"])
            if parameters.validated_data["sort"]
            else RankedFeedPagination(timestamp)
        )
        queryset = counted_collection(
            library_queryset(request.user, parameters.validated_data)
        )
        entries, next_cursor = pagination.page(
            queryset,
            parameters.validated_data,
            cursor_context(parameters.validated_data),
        )
        return Response(
            {
                "entries": LibraryBookSerializer(entries, many=True).data,
                "next_cursor": next_cursor,
                "has_more": next_cursor is not None,
                "pagination": collection_pagination(
                    queryset, parameters.validated_data, entries
                ),
            }
        )


class MyBookDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="my_book_detail",
        responses={
            200: PersonalBookDetailSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, slug):
        queryset = with_public_relations(
            visible_personal_books(request.user).only(
                *PUBLIC_BOOK_FIELDS,
                "summary",
                "publisher",
                "is_compilation",
                *EDITORIAL_DETAIL_FIELDS,
            )
        )
        book = catalog_object_by_slug(queryset, slug)
        return Response(
            PersonalBookDetailSerializer(book, context={"request": request}).data
        )
