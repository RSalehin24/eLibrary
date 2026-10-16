from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.workspaces import management_sections
from apps.catalog.discovery.management import managed_book_queryset
from apps.catalog.editorial.creation import create_catalog_book
from apps.catalog.models import Book
from apps.catalog.serializers.creation import BookCreateSerializer
from apps.catalog.serializers.management import ManagedBookDetailSerializer
from apps.catalog.serializers.public import (
    AdminBookCollectionSerializer,
    AdminBookListSerializer,
    AdminBookParametersSerializer,
)
from apps.catalog.views.editorial import managed_book_by_slug
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination


class ManagedBookListView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_book_create",
        request=BookCreateSerializer,
        responses={
            201: ManagedBookDetailSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def post(self, request):
        parameters = BookCreateSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        book = create_catalog_book(request.user, parameters.validated_data)
        return Response(
            ManagedBookDetailSerializer(
                managed_book_by_slug(request.user, book.slug)
            ).data,
            status=201,
        )

    @extend_schema(
        operation_id="managed_books_list",
        parameters=[AdminBookParametersSerializer],
        responses={
            200: AdminBookCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        if "books" not in management_sections(request.user):
            raise PermissionDenied("Metadata management access is required.")
        parameters = AdminBookParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        queryset = managed_book_queryset(request.user, parameters.validated_data)
        pagination = BoundedAdminPagination()
        entries: list[Book] | None = pagination.paginate_queryset(
            queryset, request, view=self
        )
        return pagination.get_paginated_response(
            AdminBookListSerializer(entries, many=True).data
        )
