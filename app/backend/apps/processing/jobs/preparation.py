from django.http import Http404

from apps.access.models import PermissionScope
from apps.access.reading.epub_paths import InvalidEpub
from apps.access.reading.preparation import prepare_epub_asset
from apps.catalog.models import GeneratedAssetStatus, GeneratedAssetType
from apps.common.permissions import user_has_scope
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def current_preparation_job(identifier):
    job = BackgroundJob.objects.select_related("requested_by", "asset", "book").get(
        pk=identifier
    )
    actor = job.requested_by
    if (
        actor is None
        or not actor.is_active
        or not user_has_scope(actor, [PermissionScope.PROCESSING_MANAGE])
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "permission_revoked")
    asset = job.asset
    if (
        job.book is None
        or asset is None
        or job.book.deleted_at
        or asset.status != GeneratedAssetStatus.READY
        or asset.asset_type != GeneratedAssetType.EPUB
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_unavailable")
    if job.input.get("asset_revision") != asset.updated_at.isoformat():
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_changed")
    return job


def prepare_checked_asset(asset):
    try:
        return prepare_epub_asset(asset)
    except InvalidEpub as error:
        raise ExecutionFailure(FailureKind.PERMANENT, "invalid_epub") from error
    except Http404 as error:
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_missing") from error
    except OSError as error:
        raise ExecutionFailure(FailureKind.TRANSIENT, "storage_unavailable") from error


def run_preparation(ownership):
    job = current_preparation_job(ownership.job_id)
    if not checkpoint_attempt(ownership, job.checkpoint, "preparing"):
        return False
    publication = prepare_checked_asset(job.asset)
    current_preparation_job(job.pk)
    checkpoint = {
        "publication_id": str(publication.pk),
        "checksum": publication.checksum,
    }
    return checkpoint_attempt(ownership, checkpoint, "prepared")
