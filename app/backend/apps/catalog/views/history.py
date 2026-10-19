from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import MetadataVersion
from apps.catalog.serializers.history import (
    MetadataHistoryCollectionSerializer,
    MetadataHistoryParametersSerializer,
    MetadataVersionSerializer,
)
from apps.catalog.views.editorial import managed_book_by_slug
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination


def metadata_history(book):
    # Older snapshots include protected book text; history never loads that payload.
    return (
        MetadataVersion.objects.filter(book=book)
        .select_related("created_by")
        .only(
            "id",
            "source",
            "notes",
            "created_at",
            "created_by_id",
            "created_by__full_name",
            "created_by__first_name",
            "created_by__last_name",
        )
        .order_by("-created_at", "-id")
    )


class ManagedBookHistoryView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_book_metadata_history",
        parameters=[MetadataHistoryParametersSerializer],
        responses={
            200: MetadataHistoryCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, slug):
        parameters = MetadataHistoryParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        book = managed_book_by_slug(request.user, slug)
        pagination = BoundedAdminPagination()
        pagination.page_size = parameters.validated_data["limit"]
        entries: list[MetadataVersion] | None = pagination.paginate_queryset(
            metadata_history(book), request, view=self
        )
        return pagination.get_paginated_response(
            MetadataVersionSerializer(entries, many=True).data
        )
