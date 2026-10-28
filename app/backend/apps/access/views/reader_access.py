from django.urls import reverse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.models import ReadingSession
from apps.access.protected_files import protected_download_response
from apps.access.publication_models import PreparationState, PreparedPublication
from apps.access.reader_serializers import (
    ReaderAccessSerializer,
    ReaderProgressSerializer,
)
from apps.access.reading.document_safety import PREPARATION_VERSION
from apps.access.reading.launch import active_reader_session
from apps.access.storage import asset_is_available
from apps.catalog.cover_urls import book_cover_url, with_cover_asset
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import Book, GeneratedAssetStatus, GeneratedAssetType
from apps.common.api import VersionedAPIView
from apps.common.permissions import (
    is_book_administrator,
    user_can_download_book_assets,
    user_can_launch_reader,
    user_can_send_to_kindle,
    user_can_view_book_cover,
    user_can_view_preview_html,
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
            with_cover_asset(Book.objects.filter(deleted_at__isnull=True)), slug
        )
        can_access = user_has_reader_access(request.user, book)
        session = active_reader_session(request.user, book) if can_access else None
        asset = book.generated_assets.filter(
            asset_type=GeneratedAssetType.EPUB, status=GeneratedAssetStatus.READY
        ).first()
        file_available = bool(asset and asset_is_available(asset))
        prepared = bool(
            can_access
            and asset
            and PreparedPublication.objects.filter(
                checksum=asset.checksum,
                state=PreparationState.READY,
                manifest__preparation_version=PREPARATION_VERSION,
            ).exists()
        )
        reading = ReadingSession.objects.filter(user=request.user, book=book).first()
        return Response(
            {
                "can_edit_book": is_book_administrator(request.user),
                "can_read": user_can_launch_reader(request.user, book),
                "can_download": bool(
                    file_available and user_can_download_book_assets(request.user, book)
                ),
                "prepared": prepared,
                "can_send_kindle": bool(
                    file_available and user_can_send_to_kindle(request.user, book)
                ),
                "active_session_id": session.pk
                if session and session.prepared_publication_id
                else None,
                "html_url": html_preview_url(request.user, book),
                "cover_url": book_cover_url(book)
                if user_can_view_book_cover(request.user, book)
                else None,
                "reading_progress": ReaderProgressSerializer(reading).data
                if reading
                else None,
                "progress_session_id": reading.preview_session_id
                if reading and can_access
                else None,
                "last_opened_at": reading.last_opened_at if reading else None,
            }
        )


def html_preview_url(actor, book):
    if not user_can_view_preview_html(actor, book):
        return None
    asset = book.generated_assets.filter(
        asset_type=GeneratedAssetType.HTML, status=GeneratedAssetStatus.READY
    ).first()
    if asset is None or not asset_is_available(asset):
        return None
    return reverse("api_v1:reader-html", kwargs={"slug": book.slug})


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
