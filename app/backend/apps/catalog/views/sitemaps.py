from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.discovery.sitemaps import (
    SITEMAP_KINDS,
    sitemap_batches,
    sitemap_entries,
)
from apps.catalog.serializers.sitemaps import (
    SitemapBatchSerializer,
    SitemapEntrySerializer,
)
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


class SitemapIndexView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_sitemap_index",
        responses={200: SitemapBatchSerializer(many=True)},
    )
    def get(self, request):
        return Response(SitemapBatchSerializer(sitemap_batches(), many=True).data)


class SitemapEntriesView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_sitemap_entries",
        parameters=[
            OpenApiParameter("kind", str, OpenApiParameter.PATH, enum=SITEMAP_KINDS)
        ],
        responses={200: SitemapEntrySerializer(many=True), 404: APIErrorSerializer},
    )
    def get(self, request, **kwargs):
        entries = sitemap_entries(kwargs["kind"], kwargs["page"])
        return Response(SitemapEntrySerializer(entries, many=True).data)
