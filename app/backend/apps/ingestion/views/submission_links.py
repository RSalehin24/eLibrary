from urllib.parse import quote

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import GeneratedAssetStatus, GeneratedAssetType
from apps.common.url_utils import public_api_url
from apps.ingestion.models import (
    SubmissionStatus,
)
from apps.ingestion.services.submissions import (
    ensure_preview_session,
)

from .querysets import (
    get_accessible_submission,
    is_public_submission,
)


class SubmissionActionLinksView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, pk):
        submission = get_accessible_submission(request, pk)
        if submission.status != SubmissionStatus.READY or not submission.linked_book_id:
            return Response(
                {"detail": "This submission is not ready yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if submission.linked_book.deleted_at:
            return Response(
                {"detail": "This book was deleted."}, status=status.HTTP_410_GONE
            )

        preview_session = ensure_preview_session(
            request.user if getattr(request.user, "is_authenticated", False) else None,
            submission.linked_book,
            submission=submission,
            allow_guest=is_public_submission(submission),
        )
        if preview_session is None:
            return Response(
                {"detail": "Could not prepare access for this book."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assets = submission.linked_book.generated_assets
        has_epub = assets.filter(
            asset_type=GeneratedAssetType.EPUB, status=GeneratedAssetStatus.READY
        ).exists()
        has_html = assets.filter(
            asset_type=GeneratedAssetType.HTML, status=GeneratedAssetStatus.READY
        ).exists()
        manifest_url = public_api_url(
            "access-reader-manifest",
            kwargs={"token": preview_session.token},
            request=request,
        )
        launch_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reader?manifest={quote(manifest_url, safe='')}"
        return Response(
            {
                "book": {
                    "title": submission.linked_book.title,
                    "slug": submission.linked_book.slug,
                },
                "launch_url": launch_url,
                "manifest_url": manifest_url,
                "epub_download_url": public_api_url(
                    "access-reader-epub",
                    kwargs={"token": preview_session.token},
                    request=request,
                )
                if has_epub
                else "",
                "html_preview_url": public_api_url(
                    "access-reader-html",
                    kwargs={"token": preview_session.token},
                    request=request,
                )
                if has_html
                else "",
                "expires_at": preview_session.expires_at,
            }
        )
