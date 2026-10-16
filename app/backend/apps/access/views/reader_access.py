from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.protected_files import protected_download_response
from apps.access.publication_models import PreparationState, PreparedPublication
from apps.access.reader_serializers import ReaderAccessSerializer
from apps.access.reading.document_safety import PREPARATION_VERSION
from apps.access.reading.launch import active_reader_session
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import Book, GeneratedAssetStatus, GeneratedAssetType
from apps.common.api import VersionedAPIView
from apps.common.permissions import (
    user_can_download_book_assets,
    user_can_launch_reader,
    user_can_send_to_kindle,
    user_has_reader_access,
)

from .shared import asset_download_filename, resolve_asset


class ReaderAccessView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="reader_access", responses={200: ReaderAccessSerializer}
    )
    def get(self, request, slug):
        book = catalog_object_by_slug(
            Book.objects.filter(deleted_at__isnull=True), slug
        )
        if book.record_type == "manual":
            return Response({"can_read": False, "can_download": False, "prepared": False, "can_send_kindle": False, "active_session_id": None})
        can_access = user_has_reader_access(request.user, book)
        session = active_reader_session(request.user, book) if can_access else None
        asset = book.generated_assets.filter(
            asset_type=GeneratedAssetType.EPUB, status=GeneratedAssetStatus.READY
        ).first()
        prepared = bool(
            can_access
            and asset
            and PreparedPublication.objects.filter(
                checksum=asset.checksum,
                state=PreparationState.READY,
                manifest__preparation_version=PREPARATION_VERSION,
            ).exists()
        )
        return Response(
            {
                "can_read": user_can_launch_reader(request.user, book),
                "can_download": bool(
                    asset and user_can_download_book_assets(request.user, book)
                ),
                "prepared": prepared,
                "can_send_kindle": bool(
                    asset and user_can_send_to_kindle(request.user, book)
                ),
                "active_session_id": session.pk
                if session and session.prepared_publication_id
                else None,
            }
        )


class ReaderDownloadView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(operation_id="reader_download", responses={200: OpenApiTypes.BINARY})
    def get(self, request, slug):
        book = catalog_object_by_slug(
            Book.objects.filter(deleted_at__isnull=True), slug
        )
        if not user_can_download_book_assets(request.user, book):
            raise PermissionDenied("You do not have download access for this book.")
        asset = resolve_asset(book, GeneratedAssetType.EPUB)
        return protected_download_response(asset, asset_download_filename(book, asset))
