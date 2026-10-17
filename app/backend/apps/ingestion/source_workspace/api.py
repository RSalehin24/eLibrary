from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination
from apps.common.permissions import CanManageProcessing
from apps.ingestion.models import SourceCatalogEntry

from .content import source_content_summary
from .queries import source_entries, source_snapshots
from .serializers import (
    SourceEntryCollectionSerializer,
    SourceEntrySerializer,
    SourceParametersSerializer,
)


class SourceEntryListView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="managed_sources_list",
        parameters=[SourceParametersSerializer],
        responses={
            200: SourceEntryCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        parameters = SourceParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        pagination = BoundedAdminPagination()
        entries: list[SourceCatalogEntry] | None = pagination.paginate_queryset(
            source_entries(parameters.validated_data), request
        )
        snapshots = source_snapshots(entries or [], request.user)
        return pagination.get_paginated_response(
            SourceEntrySerializer(snapshots, many=True).data
        )


class SourceEntryDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageProcessing)

    @extend_schema(
        operation_id="managed_source_read",
        responses={
            200: SourceEntrySerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        entry = get_object_or_404(
            source_entries({"q": "", "status": "all"}), pk=identifier
        )
        snapshot = source_snapshots([entry], request.user)[0]
        return Response(
            SourceEntrySerializer(
                snapshot,
                context={"content_summary": source_content_summary(snapshot.book)},
            ).data
        )
