from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.discovery.management import metadata_managed_books
from apps.catalog.discovery.queries import PUBLIC_BOOK_FIELDS, with_public_relations
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.editorial.service import update_book_editorial, withdraw_book
from apps.catalog.serializers.editorial import (
    EDITORIAL_DETAIL_FIELDS,
    BookEditorialUpdateSerializer,
    ExpectedRevisionSerializer,
)
from apps.catalog.serializers.formats import BOOK_FORMAT_FIELDS
from apps.catalog.serializers.management import ManagedBookDetailSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer

DETAIL_RESPONSES = {
    200: ManagedBookDetailSerializer,
    403: APIErrorSerializer,
    404: APIErrorSerializer,
}
COMMAND_RESPONSES = {
    **DETAIL_RESPONSES,
    400: APIErrorSerializer,
    409: APIErrorSerializer,
}


def managed_book_by_slug(user, slug):
    queryset = metadata_managed_books(user).only(
        *PUBLIC_BOOK_FIELDS,
        "summary",
        "state",
        "updated_at",
        *BOOK_FORMAT_FIELDS,
        *EDITORIAL_DETAIL_FIELDS,
    )
    return catalog_object_by_slug(with_public_relations(queryset), slug)


def editorial_command(request, slug, operation):
    parameters = ExpectedRevisionSerializer(data=request.data)
    parameters.is_valid(raise_exception=True)
    book = managed_book_by_slug(request.user, slug)
    updated = operation(
        request.user, book.pk, parameters.validated_data["expected_updated_at"]
    )
    return Response(
        ManagedBookDetailSerializer(
            managed_book_by_slug(request.user, updated.slug)
        ).data
    )


class ManagedBookDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(operation_id="managed_book_detail", responses=DETAIL_RESPONSES)
    def get(self, request, slug):
        return Response(
            ManagedBookDetailSerializer(managed_book_by_slug(request.user, slug)).data
        )

    @extend_schema(
        operation_id="managed_book_editorial_update",
        request=BookEditorialUpdateSerializer,
        responses=COMMAND_RESPONSES,
    )
    def patch(self, request, slug):
        parameters = BookEditorialUpdateSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        book = managed_book_by_slug(request.user, slug)
        updated = update_book_editorial(
            request.user, book.pk, parameters.validated_data
        )
        return Response(
            ManagedBookDetailSerializer(
                managed_book_by_slug(request.user, updated.slug)
            ).data
        )

    @extend_schema(
        operation_id="managed_book_remove",
        request=ExpectedRevisionSerializer,
        responses={
            204: None,
            **{key: value for key, value in COMMAND_RESPONSES.items() if key != 200},
        },
    )
    def delete(self, request, slug):
        from .book_controls import remove_book_response

        return remove_book_response(request, slug)


class WithdrawBookView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_book_withdraw",
        request=ExpectedRevisionSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, slug):
        return editorial_command(request, slug, withdraw_book)
