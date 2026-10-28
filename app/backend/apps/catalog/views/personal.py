from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.models import SavedBook
from apps.catalog.reading.personal import personal_book, set_saved_book
from apps.catalog.serializers.personal import SavedBookSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer

PERSONAL_ERRORS = {
    400: APIErrorSerializer,
    403: APIErrorSerializer,
    404: APIErrorSerializer,
    409: APIErrorSerializer,
}


class SavedBookView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="saved_book",
        responses={200: SavedBookSerializer, **PERSONAL_ERRORS},
    )
    def get(self, request, slug):
        book = personal_book(request.user, slug)
        return Response(
            {"saved": SavedBook.objects.filter(user=request.user, book=book).exists()}
        )

    @extend_schema(
        operation_id="saved_book_update",
        request=SavedBookSerializer,
        responses={200: SavedBookSerializer, **PERSONAL_ERRORS},
    )
    def put(self, request, slug):
        serializer = SavedBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "saved": set_saved_book(
                    request.user, slug, serializer.validated_data["saved"]
                )
            }
        )
