from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.accounts.workspaces import management_sections
from apps.catalog.discovery.exports import (
    ordered_export_queryset,
    physical_book_queryset,
)
from apps.catalog.discovery.library import library_queryset
from apps.catalog.discovery.management import managed_book_queryset
from apps.catalog.discovery.queries import PUBLIC_BOOK_FIELDS, discovery_queryset
from apps.catalog.exports import build_books_csv_response
from apps.catalog.exports.grouped_pdf import build_grouped_pdf_response
from apps.catalog.exports.print_exports import build_print_response
from apps.catalog.exports.xlsx_exports import build_physical_xlsx_response
from apps.catalog.models import Book
from apps.catalog.serializers.exports import (
    CatalogExportParametersSerializer,
    LibraryExportParametersSerializer,
    PhysicalBookCollectionSerializer,
    PhysicalBookExportParametersSerializer,
    PhysicalBookParametersSerializer,
)
from apps.catalog.serializers.public import PublicBookDetailSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination

EXPORT_RESPONSES = {
    (200, "text/csv"): OpenApiTypes.BINARY,
    (200, "application/pdf"): OpenApiTypes.BINARY,
    (200, "text/html"): OpenApiTypes.STR,
    400: APIErrorSerializer,
    403: APIErrorSerializer,
    503: APIErrorSerializer,
}


def parameters_for(serializer_type, request):
    serializer = serializer_type(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def export_response(queryset, parameters):
    # Exports include the entire filtered set, independently of the list page.
    books = list(
        queryset.only(
            *PUBLIC_BOOK_FIELDS,
            "record_type",
            "manual_binding",
            "manual_publisher",
            "manual_price",
            "manual_is_compilation",
        )
    )
    selected_format = parameters["export_format"]
    if selected_format == "xlsx":
        return build_physical_xlsx_response(books, parameters["group_by"])
    if selected_format == "csv":
        return build_books_csv_response(books, record_type=parameters["record_type"])
    if selected_format == "print":
        return build_print_response(books, parameters.get("group_by", ""))
    try:
        return build_grouped_pdf_response(books, parameters.get("group_by", ""))
    except RuntimeError as error:
        exception = APIException(str(error))
        exception.status_code = 503
        raise exception from error


class CatalogExportView(VersionedAPIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_books_export",
        parameters=[CatalogExportParametersSerializer],
        responses=EXPORT_RESPONSES,
    )
    def get(self, request):
        parameters = parameters_for(CatalogExportParametersSerializer, request)
        return export_response(
            ordered_export_queryset(
                discovery_queryset(parameters, request.user), parameters
            ),
            parameters,
        )


class LibraryExportView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="my_books_export",
        parameters=[LibraryExportParametersSerializer],
        responses=EXPORT_RESPONSES,
    )
    def get(self, request):
        parameters = parameters_for(LibraryExportParametersSerializer, request)
        return export_response(
            ordered_export_queryset(
                library_queryset(request.user, parameters), parameters
            ),
            parameters,
        )


class ManagedBooksExportView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_books_export",
        parameters=[CatalogExportParametersSerializer],
        responses=EXPORT_RESPONSES,
    )
    def get(self, request):
        if "books" not in management_sections(request.user):
            raise PermissionDenied("Metadata management access is required.")
        parameters = parameters_for(CatalogExportParametersSerializer, request)
        return export_response(
            managed_book_queryset(request.user, parameters), parameters
        )


class PhysicalBooksView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="physical_books_list",
        parameters=[PhysicalBookParametersSerializer],
        responses={
            200: PhysicalBookCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        parameters = parameters_for(PhysicalBookParametersSerializer, request)
        queryset = physical_book_queryset(request.user, parameters)
        pagination = BoundedAdminPagination()
        entries: list[Book] | None = pagination.paginate_queryset(
            queryset, request, view=self
        )
        return pagination.get_paginated_response(
            PublicBookDetailSerializer(entries, many=True).data
        )


class PhysicalBooksExportView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="physical_books_export",
        parameters=[PhysicalBookExportParametersSerializer],
        responses={
            **EXPORT_RESPONSES,
            (
                200,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ): OpenApiTypes.BINARY,
        },
    )
    def get(self, request):
        parameters = parameters_for(PhysicalBookExportParametersSerializer, request)
        parameters["record_type"] = "manual"
        return export_response(
            physical_book_queryset(request.user, parameters), parameters
        )
