from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.reading.list_controls import book_list_controls
from apps.catalog.serializers.list_controls import (
    BookListControlParametersSerializer,
    BookListControlsSerializer,
)
from apps.common.api import VersionedAPIView


class BookListControlsView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="book_list_controls",
        parameters=[BookListControlParametersSerializer],
        responses={200: BookListControlsSerializer},
    )
    def get(self, request):
        parameters = BookListControlParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        return Response(
            {
                "entries": book_list_controls(
                    request.user, parameters.validated_data["slugs"]
                )
            }
        )
