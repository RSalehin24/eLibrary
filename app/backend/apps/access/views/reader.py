import mimetypes
import zipfile
from io import BytesIO
from urllib.parse import quote, unquote

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import Bookmark, Highlight, PreviewAccessSession
from apps.access.serializers import BookmarkSerializer, HighlightSerializer, ReadingSessionSerializer
from apps.catalog.models import Book, GeneratedAssetType
from apps.common.permissions import user_can_launch_reader
from apps.common.url_utils import public_api_url

from .preview_html import html_asset_response
from .shared import (
    apply_no_store_headers,
    asset_download_filename,
    asset_is_available,
    default_preview_expiry,
    get_active_preview_session,
    get_token_preview_session,
    missing_asset_response,
    open_asset_stream,
    read_asset_bytes,
    reading_session_for_book,
    resolve_asset,
)


class ReaderLaunchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        book = get_object_or_404(Book, slug=slug)

        from apps.common.permissions import user_has_read_once_limit, user_has_scope, user_owns_book
        if not request.user.is_superuser and not user_owns_book(request.user, book):
            if user_has_read_once_limit(request.user, book):
                raise PermissionDenied("You have already opened this book under the Read Once permission.")

        allowed = user_can_launch_reader(request.user, book)
        session = get_active_preview_session(request.user, book)
        if not allowed and session is None:
            raise PermissionDenied("You do not have reader access for this book.")

        from apps.access.models import PermissionScope
        if (
            not request.user.is_superuser
            and not user_owns_book(request.user, book)
            and user_has_scope(request.user, [PermissionScope.READ_ONCE], book=book)
            and not user_has_scope(request.user, [PermissionScope.READ_DURABLE], book=book)
        ):
            from apps.access.models import BookOpeningRecord
            BookOpeningRecord.objects.get_or_create(user=request.user, book=book)

        if session is None:
            session = PreviewAccessSession.objects.create(user=request.user, book=book)

        session.launch_count += 1
        session.expires_at = default_preview_expiry()
        session.save(update_fields=["launch_count", "expires_at", "updated_at"])
        manifest_url = public_api_url("access-reader-manifest", kwargs={"token": session.token}, request=request)
        launch_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reader?manifest={quote(manifest_url, safe='')}"
        return Response(
            {
                "launch_url": launch_url,
                "manifest_url": manifest_url,
                "expires_at": session.expires_at,
            }
        )


class ReaderManifestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        session = get_token_preview_session(token)
        epub_asset = session.book.generated_assets.filter(asset_type=GeneratedAssetType.EPUB).first()
        html_asset = session.book.generated_assets.filter(asset_type=GeneratedAssetType.HTML).first()
        if epub_asset is None:
            raise Http404("EPUB asset is unavailable.")
        if not asset_is_available(epub_asset):
            return missing_asset_response(session.book, epub_asset, actor=session.user)

        reading_session = None
        bookmarks = []
        highlights = []
        reading_session_url = ""
        bookmarks_url = ""
        highlights_url = ""
        if session.user_id:
            reading_session, _ = reading_session_for_book(session.user, session.book, preview_session=session)
            bookmarks = Bookmark.objects.filter(user=session.user, book=session.book)
            highlights = Highlight.objects.filter(user=session.user, book=session.book)
            reading_session_url = public_api_url("access-reader-session", kwargs={"token": session.token}, request=request)
            bookmarks_url = public_api_url("access-reader-bookmark-list", kwargs={"token": session.token}, request=request)
            highlights_url = public_api_url("access-reader-highlight-list", kwargs={"token": session.token}, request=request)

        response = Response(
            {
                "book": {"title": session.book.title, "slug": session.book.slug},
                "epub_download_url": public_api_url("access-reader-epub", kwargs={"token": session.token}, request=request),
                "html_preview_url": public_api_url("access-reader-html", kwargs={"token": session.token}, request=request)
                if html_asset and asset_is_available(html_asset)
                else "",
                "reading_session_url": reading_session_url,
                "bookmarks_url": bookmarks_url,
                "highlights_url": highlights_url,
                "reading_session": ReadingSessionSerializer(reading_session).data if reading_session else None,
                "bookmarks": BookmarkSerializer(bookmarks, many=True).data if bookmarks else [],
                "highlights": HighlightSerializer(highlights, many=True).data if highlights else [],
            }
        )
        return apply_no_store_headers(response)


class ReaderEpubDownloadView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token, asset_path=""):
        session = get_token_preview_session(token)
        asset = resolve_asset(session.book, GeneratedAssetType.EPUB)
        if not asset_is_available(asset):
            return missing_asset_response(session.book, asset, actor=session.user)
        if asset_path:
            return self.epub_entry_response(asset, self.normalize_epub_asset_path(asset_path))
        response = FileResponse(
            open_asset_stream(asset),
            as_attachment=False,
            filename=asset_download_filename(session.book, asset),
        )
        return apply_no_store_headers(response)

    def normalize_epub_asset_path(self, raw_path):
        decoded = unquote(raw_path or "")
        sanitized = decoded.replace("\\", "/").lstrip("/")
        if not sanitized or ".." in sanitized.split("/"):
            raise Http404("Invalid EPUB resource path.")
        return sanitized

    def epub_entry_response(self, asset, entry_path):
        payload, _name, local_path = read_asset_bytes(asset)
        try:
            if local_path:
                with zipfile.ZipFile(local_path, "r") as archive:
                    data = archive.read(entry_path)
            else:
                with zipfile.ZipFile(BytesIO(payload), "r") as archive:
                    data = archive.read(entry_path)
        except KeyError as exc:
            raise Http404("EPUB resource not found.") from exc
        except zipfile.BadZipFile as exc:
            raise Http404("EPUB file is invalid.") from exc

        response = HttpResponse(data, content_type=mimetypes.guess_type(entry_path)[0] or "application/octet-stream")
        return apply_no_store_headers(response)


class ReaderHtmlPreviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        session = get_token_preview_session(token)
        asset = resolve_asset(session.book, GeneratedAssetType.HTML)
        if not asset_is_available(asset):
            return missing_asset_response(session.book, asset, actor=session.user)
        return apply_no_store_headers(html_asset_response(session.book, asset))


__all__ = [
    "ReaderEpubDownloadView",
    "ReaderHtmlPreviewView",
    "ReaderLaunchView",
    "ReaderManifestView",
]
