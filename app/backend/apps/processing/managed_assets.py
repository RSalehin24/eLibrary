from django.db.models import Exists, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.exceptions import PermissionDenied

from apps.access.asset_names import asset_download_filename
from apps.access.protected_files import protected_download_response
from apps.access.publication_models import PreparationState, PreparedPublication
from apps.access.reading.document_safety import PREPARATION_VERSION
from apps.access.reading.epub_manifest import READER_MANIFEST_VERSION
from apps.access.storage import asset_is_available
from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus
from apps.common.api import VersionedAPIView
from apps.common.permissions import CanManageProcessing, user_can_download_book_assets
from apps.processing.job_models import SOURCE_ACTIVE_STATES, BackgroundJob


def processing_assets(book, actor):
    preparations = BackgroundJob.objects.filter(
        Q(asset_id=OuterRef("pk"), kind="prepare_epub")
        | Q(book_id=OuterRef("book_id"), kind="process_source")
    ).filter(state__in=SOURCE_ACTIVE_STATES)
    publications = PreparedPublication.objects.filter(
        checksum=OuterRef("checksum"),
        state=PreparationState.READY,
        manifest__preparation_version=PREPARATION_VERSION,
    )
    outdated_publications = publications.filter(
        Q(manifest__manifest_version__isnull=True)
        | ~Q(manifest__manifest_version=READER_MANIFEST_VERSION)
    )
    assets = list(
        book.generated_assets.order_by("asset_type").annotate(
            reader_ready=Exists(publications),
            reader_update_available=Exists(outdated_publications),
            active_preparation_id=Subquery(preparations.values("id")[:1]),
        )
    )
    can_download = actor.is_active and user_can_download_book_assets(actor, book)
    for asset in assets:
        asset.file_available = (
            asset.status == GeneratedAssetStatus.READY and asset_is_available(asset)
        )
        asset.download_url = (
            reverse("api_v1:managed-asset-download", kwargs={"identifier": asset.pk})
            if can_download
            and asset.file_available
            and asset.asset_type in {"epub", "html"}
            else None
        )
    return assets


class ManagedAssetDownloadView(VersionedAPIView):
    permission_classes = (CanManageProcessing,)

    @extend_schema(
        operation_id="managed_asset_download", responses={200: OpenApiTypes.BINARY}
    )
    def get(self, request, identifier):
        if not request.user.is_active:
            raise PermissionDenied("This account is disabled.")
        asset = get_object_or_404(
            GeneratedAsset.objects.select_related("book"),
            pk=identifier,
            status=GeneratedAssetStatus.READY,
            asset_type__in=("epub", "html"),
            book__deleted_at__isnull=True,
        )
        if not user_can_download_book_assets(request.user, asset.book):
            raise PermissionDenied("You do not have download access for this book.")
        response = protected_download_response(
            asset, asset_download_filename(asset.book, asset)
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "sandbox"
        return response
