from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.editorial.covers import replace_book_cover
from apps.catalog.serializers.editorial import ExpectedRevisionSerializer
from apps.catalog.serializers.management import ManagedBookDetailSerializer
from apps.catalog.views.editorial import COMMAND_RESPONSES, managed_book_by_slug
from apps.common.api import VersionedAPIView
from apps.common.images import MAX_IMAGE_SIDE_PIXELS, normalized_uploaded_image
from apps.common.validation import reject_unknown_fields


class CoverCommandSerializer(ExpectedRevisionSerializer):
    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class CoverUploadSerializer(CoverCommandSerializer):
    image = serializers.FileField()

    def validate_image(self, value):
        return normalized_uploaded_image(value, MAX_IMAGE_SIDE_PIXELS)


def edit_cover_response(request, slug, serializer_type):
    book = managed_book_by_slug(request.user, slug)
    command = serializer_type(data=request.data)
    command.is_valid(raise_exception=True)
    updated = replace_book_cover(request.user, book.pk, command.validated_data)
    return Response(
        ManagedBookDetailSerializer(
            managed_book_by_slug(request.user, updated.slug)
        ).data
    )


class ManagedBookCoverView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, JSONParser)

    @extend_schema(
        operation_id="managed_book_cover_upload",
        request=CoverUploadSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, slug):
        return edit_cover_response(request, slug, CoverUploadSerializer)

    @extend_schema(
        operation_id="managed_book_cover_remove",
        request=CoverCommandSerializer,
        responses=COMMAND_RESPONSES,
    )
    def delete(self, request, slug):
        return edit_cover_response(request, slug, CoverCommandSerializer)
