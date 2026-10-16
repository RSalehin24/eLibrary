from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.editorial.creation import created_book
from apps.catalog.serializers.management import ManagedBookDetailSerializer
from apps.catalog.views.editorial import managed_book_by_slug
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


class ManagedBookCreationView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_book_creation_status",
        responses={
            200: ManagedBookDetailSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        book = created_book(request.user, identifier)
        return Response(
            ManagedBookDetailSerializer(
                managed_book_by_slug(request.user, book.slug)
            ).data
        )
