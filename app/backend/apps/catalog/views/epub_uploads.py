from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.editorial.epub_uploads import (
    replace_managed_epub,
    validate_epub_upload,
)
from apps.catalog.serializers.management import ManagedBookDetailSerializer
from apps.catalog.views.editorial import COMMAND_RESPONSES, managed_book_by_slug
from apps.common.api import VersionedAPIView
from apps.common.validation import reject_unknown_fields


class ManagedEpubUploadSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    file = serializers.FileField()

    def validate_file(self, value):
        validate_epub_upload(value)
        return value

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class ManagedEpubUploadView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    @extend_schema(
        operation_id="managed_book_epub_upload",
        request=ManagedEpubUploadSerializer,
        responses=COMMAND_RESPONSES,
    )
    def post(self, request, slug):
        book = managed_book_by_slug(request.user, slug)
        parameters = ManagedEpubUploadSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        updated = replace_managed_epub(request.user, book.pk, parameters.validated_data)
        return Response(
            ManagedBookDetailSerializer(
                managed_book_by_slug(request.user, updated.slug)
            ).data
        )
