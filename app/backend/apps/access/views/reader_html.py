from django.http import Http404
from django.utils.http import content_disposition_header
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.access.asset_names import asset_download_filename
from apps.access.protected_files import protected_download_response
from apps.access.reading.launch import authorize_html_opening
from apps.access.storage import asset_is_available
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import Book, GeneratedAssetType
from apps.common.api import VersionedAPIView

from .shared import resolve_asset


class ReaderHTMLView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_html", responses={(200, "text/html"): OpenApiTypes.BINARY}
    )
    def get(self, request, slug):
        if not request.user.is_active:
            raise PermissionDenied("This account is disabled.")
        book = catalog_object_by_slug(
            Book.objects.filter(deleted_at__isnull=True), slug
        )
        asset = resolve_asset(book, GeneratedAssetType.HTML)
        if not asset_is_available(asset):
            raise Http404("The HTML file is unavailable.")
        authorize_html_opening(request.user, book)
        filename = asset_download_filename(book, asset)
        response = protected_download_response(asset, filename)
        response["Content-Disposition"] = content_disposition_header(False, filename)
        response["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
            "font-src data:; media-src data:; base-uri 'none'; form-action 'none'; sandbox"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "no-referrer"
        return response
