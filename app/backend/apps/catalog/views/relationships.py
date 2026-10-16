from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.editorial.creation import require_catalog_creator
from apps.catalog.editorial.relationships import (
    relationship_details,
    update_relationships,
)
from apps.catalog.serializers.relationships import (
    BookRelationshipsSerializer,
    BookRelationshipsUpdateSerializer,
)
from apps.catalog.views.editorial import managed_book_by_slug
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer

RELATIONSHIP_RESPONSES = {
    200: BookRelationshipsSerializer,
    400: APIErrorSerializer,
    403: APIErrorSerializer,
    404: APIErrorSerializer,
    409: APIErrorSerializer,
}


class BookRelationshipsView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_book_relationships", responses=RELATIONSHIP_RESPONSES
    )
    def get(self, request, slug):
        require_catalog_creator(request.user)
        book = managed_book_by_slug(request.user, slug)
        return Response(BookRelationshipsSerializer(relationship_details(book)).data)

    @extend_schema(
        operation_id="managed_book_relationships_update",
        request=BookRelationshipsUpdateSerializer,
        responses=RELATIONSHIP_RESPONSES,
    )
    def patch(self, request, slug):
        require_catalog_creator(request.user)
        parameters = BookRelationshipsUpdateSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        book = managed_book_by_slug(request.user, slug)
        updated = update_relationships(request.user, book.pk, parameters.validated_data)
        return Response(BookRelationshipsSerializer(relationship_details(updated)).data)
