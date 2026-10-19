from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from apps.processing.jobs.preparation import prepare_checked_asset

from .guards import require_export_authority
from .queries import current_source_job


def checked_source_asset(job):
    staged = job.checkpoint.get("staged_assets", {}).get("epub")
    if staged and not job.checkpoint.get("assets_published"):
        return GeneratedAsset(book_id=job.book_id, asset_type="epub", **staged)
    asset = job.asset
    if asset is None or asset.status != GeneratedAssetStatus.READY:
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_unavailable")
    if asset.updated_at.isoformat() != job.checkpoint.get(
        "asset_revision"
    ) or asset.checksum != job.checkpoint.get("asset_checksum"):
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_asset_changed")
    return asset


def prepare_source_reading(ownership):
    require_export_authority(ownership)
    job = current_source_job(ownership.job_id)
    asset = checked_source_asset(job)
    if not checkpoint_attempt(ownership, job.checkpoint, "preparing"):
        return False
    publication = prepare_checked_asset(asset)
    require_export_authority(ownership)
    current = current_source_job(job.pk)
    checked_source_asset(current)
    if publication.checksum != asset.checksum:
        raise ExecutionFailure(FailureKind.UNCERTAIN, "source_asset_changed")
    checkpoint = {
        **current.checkpoint,
        "publication_id": str(publication.pk),
        "checksum": publication.checksum,
    }
    return checkpoint_attempt(ownership, checkpoint, "source_prepared")
