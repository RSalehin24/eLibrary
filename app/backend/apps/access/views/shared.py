import logging
from pathlib import Path

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.access.asset_names import (
    asset_download_filename,
    asset_source_name,
    safe_download_stem,
)
from apps.access.models import (
    Bookmark,
    PermissionScope,
    PreviewAccessSession,
    ReadingSession,
    default_preview_expiry,
)
from apps.access.reading.launch import active_reader_session
from apps.access.storage import asset_file_exists, open_asset_stream
from apps.catalog.models import GeneratedAssetStatus
from apps.common.models import LifecycleState, ReviewState
from apps.common.permissions import user_has_scope

logger = logging.getLogger(__name__)


def apply_no_store_headers(response):
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def get_active_preview_session(user, book):
    return active_reader_session(user, book)


def get_token_preview_session(token):
    session = (
        PreviewAccessSession.objects.select_related("book", "user")
        .filter(token=token)
        .first()
    )
    if session is None or not session.is_active:
        raise Http404("Reader session is unavailable.")
    return session


def get_authenticated_token_preview_session(request, token):
    session = get_token_preview_session(token)
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Sign in is required to access the reader.")
    if session.user_id != user.id:
        raise PermissionDenied("This reader session does not belong to your account.")
    return session


def resolve_asset(book, asset_type):
    asset = book.generated_assets.filter(
        asset_type=asset_type, status=GeneratedAssetStatus.READY
    ).first()
    if asset is None:
        raise Http404("Requested asset does not exist.")
    return asset


def local_asset_path(asset):
    if asset is None:
        return None

    if asset.file and asset.file.name:
        try:
            path = Path(asset.file.path)
            if path.exists():
                return path
        except (AttributeError, NotImplementedError, ValueError):
            pass

    if asset.legacy_path:
        path = Path(asset.legacy_path)
        if path.exists():
            return path

    return None


def read_asset_bytes(asset):
    path = local_asset_path(asset)
    if path and path.exists():
        return path.read_bytes(), path.name, path

    if asset.file and asset.file.name and asset_file_exists(asset.file):
        asset.file.open("rb")
        try:
            return asset.file.read(), Path(asset.file.name).name, None
        finally:
            asset.file.close()

    raise Http404("Asset file is not available.")


def asset_is_available(asset):
    if asset is None:
        return False
    if asset.file and asset.file.name and asset_file_exists(asset.file):
        return True
    if asset.legacy_path:
        return Path(asset.legacy_path).exists()
    return False


def clear_missing_asset(asset):
    update_fields = []
    if asset.status != GeneratedAssetStatus.FAILED:
        asset.status = GeneratedAssetStatus.FAILED
        update_fields.append("status")
    if asset.file and asset.file.name:
        asset.file = ""
        update_fields.append("file")
    if asset.storage_path:
        asset.storage_path = ""
        update_fields.append("storage_path")
    if asset.legacy_path:
        asset.legacy_path = ""
        update_fields.append("legacy_path")
    if asset.file_size:
        asset.file_size = 0
        update_fields.append("file_size")
    if update_fields:
        asset.save(update_fields=[*update_fields, "updated_at"])


def queue_missing_asset_recovery(book, actor=None):
    from apps.ingestion.services.submissions import (
        primary_source_url_for_book,
        queue_reprocess_book,
    )

    if not primary_source_url_for_book(book):
        return None, False

    try:
        return queue_reprocess_book(book, actor=actor)
    except Exception:
        logger.warning(
            "Could not queue regeneration for missing asset on book %s",
            book.pk,
            exc_info=True,
        )
        return None, False


def missing_asset_response(book, asset, actor=None):
    clear_missing_asset(asset)
    job, _created = queue_missing_asset_recovery(book, actor=actor)
    if job is not None:
        return Response(
            {
                "detail": "This file was missing from storage. Regeneration has been queued.",
                "job_id": str(job.id),
                "status": job.status,
            },
            status=status.HTTP_409_CONFLICT,
        )

    book_update_fields = []
    if book.state != LifecycleState.NEEDS_REVIEW:
        book.state = LifecycleState.NEEDS_REVIEW
        book_update_fields.append("state")
    if book.review_state != ReviewState.NEEDS_REVIEW:
        book.review_state = ReviewState.NEEDS_REVIEW
        book_update_fields.append("review_state")
    if book_update_fields:
        book.save(update_fields=[*book_update_fields, "updated_at"])

    return Response(
        {
            "detail": "This file is no longer available in storage. Please regenerate the book."
        },
        status=status.HTTP_404_NOT_FOUND,
    )


def ensure_book_reader_access(request, book):
    allowed = user_has_scope(
        request.user,
        [
            PermissionScope.PREVIEW_HTML,
            PermissionScope.READ_DURABLE,
            PermissionScope.DOWNLOAD_FILE,
            PermissionScope.READ_ONCE,
        ],
        book=book,
    )
    if not allowed and get_active_preview_session(request.user, book) is None:
        raise PermissionDenied("You do not have reader access for this book.")


def reading_session_for_book(user, book, *, preview_session=None):
    return ReadingSession.objects.get_or_create(
        user=user,
        book=book,
        defaults={"preview_session": preview_session} if preview_session else {},
    )


def bookmark_queryset_for_book(user, book):
    return Bookmark.objects.filter(user=user, book=book)


__all__ = [
    "apply_no_store_headers",
    "asset_download_filename",
    "asset_is_available",
    "asset_source_name",
    "bookmark_queryset_for_book",
    "default_preview_expiry",
    "ensure_book_reader_access",
    "get_active_preview_session",
    "get_authenticated_token_preview_session",
    "get_token_preview_session",
    "local_asset_path",
    "missing_asset_response",
    "open_asset_stream",
    "read_asset_bytes",
    "reading_session_for_book",
    "resolve_asset",
    "safe_download_stem",
]
