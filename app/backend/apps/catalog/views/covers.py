import mimetypes

from django.http import Http404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny

from apps.access.asset_names import asset_download_filename
from apps.access.protected_files import protected_download_response
from apps.catalog.discovery.publication import public_books
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.models import Book
from apps.common.api import VersionedAPIView
from apps.common.permissions import user_can_view_book_cover


class BookCoverView(VersionedAPIView):
    permission_classes = (AllowAny,)

    @extend_schema(operation_id="book_cover", responses={200: OpenApiTypes.BINARY})
    def get(self, request, slug):
        book = catalog_object_by_slug(
            Book.objects.filter(deleted_at__isnull=True), slug
        )
        public = public_books().filter(pk=book.pk).exists()
        actor = request.user
        if not public and not (
            actor.is_authenticated
            and actor.is_active
            and not actor.requires_totp_setup
            and user_can_view_book_cover(actor, book)
        ):
            raise PermissionDenied("You do not have cover access for this book.")
        asset = book.generated_assets.filter(asset_type="cover", status="ready").first()
        if asset is None:
            raise Http404("The book cover is unavailable.")
        content_type = (
            asset.content_type
            or mimetypes.guess_type(asset.file.name or asset.legacy_path)[0]
        )
        if content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            raise Http404("The book cover is unavailable.")
        response = protected_download_response(
            asset, asset_download_filename(book, asset)
        )
        response["Content-Type"] = content_type
        response["Content-Disposition"] = "inline"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response
