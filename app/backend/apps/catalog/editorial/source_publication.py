from apps.access.publication_models import PreparationState, PreparedPublication
from apps.catalog.models import GeneratedAssetStatus, GeneratedAssetType
from apps.processing.job_models import BackgroundJobKind, BackgroundJobState
from django.db.models import Q


def source_publication_problem(book):
    operations = book.background_jobs.filter(
        kind=BackgroundJobKind.PROCESS_SOURCE
    ).filter(
        Q(checkpoint__resolution__isnull=True)
        | ~Q(checkpoint__resolution="linked_existing")
    )
    if not operations.exists():
        return None
    if operations.exclude(
        state__in=[BackgroundJobState.SUCCEEDED, BackgroundJobState.CANCELLED]
    ).exists():
        return "Finish or resolve the source operation before publication."
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
