from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.detail_preview_serializers import BookDetailPreviewSerializer
from apps.access.reading.detail_preview import book_detail_preview
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import Book
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.permissions import user_can_launch_reader


class BookDetailPreviewView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="book_detail_preview",
        responses={
            200: BookDetailPreviewSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, slug):
        book = catalog_object_by_slug(
            Book.objects.filter(deleted_at__isnull=True), slug
        )
        if not user_can_launch_reader(request.user, book):
            raise PermissionDenied("You do not have reading access for this book.")
        return Response(BookDetailPreviewSerializer(book_detail_preview(book)).data)
