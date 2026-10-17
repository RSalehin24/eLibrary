from apps.access.publication_models import PreparationState, PreparedPublication
from apps.catalog.models import GeneratedAssetStatus, GeneratedAssetType
from apps.processing.job_models import BackgroundJobKind, BackgroundJobState
from django.db.models import Q


def source_publication_problem(book, completing_operation=None):
    operations = book.background_jobs.filter(
        kind=BackgroundJobKind.PROCESS_SOURCE
    ).filter(
        Q(checkpoint__resolution__isnull=True)
        | ~Q(checkpoint__resolution="linked_existing")
    )
    if not operations.exists():
        if book.source_urls.exists():
            return "Regenerate the source book to verify its complete text and files."
        return None
    if (
        operations.exclude(pk=completing_operation)
        .exclude(state__in=[BackgroundJobState.SUCCEEDED, BackgroundJobState.CANCELLED])
        .exists()
    ):
        return "Finish or resolve the source operation before publication."
    latest = operations.order_by("-created_at", "-pk").first()
    if not (
        latest.checkpoint.get("source_summary", {})
        .get("verification", {})
        .get("verified")
        and latest.checkpoint.get("exports_verified")
    ):
        return "Regenerate the source book to verify its complete text and files."
    ready = set(
        book.generated_assets.filter(status=GeneratedAssetStatus.READY).values_list(
            "asset_type", flat=True
        )
    )
    if not {GeneratedAssetType.HTML, GeneratedAssetType.EPUB}.issubset(ready):
        return "Prepare the source book's HTML and EPUB before publication."
    checksum = (
        book.generated_assets.filter(asset_type=GeneratedAssetType.EPUB)
        .values_list("checksum", flat=True)
        .get()
    )
    if not PreparedPublication.objects.filter(
        checksum=checksum, state=PreparationState.READY
    ).exists():
        return "Prepare the source book's reader resources before publication."
    return None
