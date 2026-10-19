from uuid import uuid4

from django.core.files import File
from django.db import transaction

from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType
from apps.ingestion.services.submissions_support.assets import (
    calculate_checksum,
    content_type_for_suffix,
)
from apps.processing.jobs.attempts import AttemptLost, checkpoint_attempt

from .documents import read_source_result
from .guards import checked_source_book, locked_source_job, require_export_authority
from .queries import current_source_job
from .regeneration import commit_regenerated_content


def stored_source_assets(ownership, paths):
    book = require_export_authority(ownership)
    storage = GeneratedAsset(book=book).file.storage
    stored = {}
    for kind, path in paths.items():
        name = f"generated/source-jobs/{ownership.job_id}/{uuid4().hex}{path.suffix}"
        with path.open("rb") as handle:
            name = storage.save(name, File(handle))
        stored[kind] = {
            "file": name,
            "storage_path": name,
            "legacy_path": "",
            "checksum": calculate_checksum(path),
            "file_size": path.stat().st_size,
            "content_type": content_type_for_suffix(path),
            "status": GeneratedAssetStatus.READY,
            "is_protected": True,
        }
    return stored


@transaction.atomic
def commit_source_assets(ownership, stored):
    job = locked_source_job(ownership)
    book = checked_source_book(job)
    if not checkpoint_attempt(ownership, job.checkpoint, "publishing_source_assets"):
        return False
    if job.input.get("regenerate_book") and not job.checkpoint.get("content_committed"):
        commit_regenerated_content(
            job, book, read_source_result(job.pk, job.checkpoint["document_ref"])
        )
    for kind, properties in stored.items():
        GeneratedAsset.objects.update_or_create(
            book=book, asset_type=kind, defaults=properties
        )
    job.asset = GeneratedAsset.objects.get(
        book=book, asset_type=GeneratedAssetType.EPUB
    )
    job.checkpoint = {
        **job.checkpoint,
        "assets_published": True,
        "asset_revision": job.asset.updated_at.isoformat(),
        "asset_checksum": job.asset.checksum,
    }
    job.save(update_fields=["asset", "checkpoint", "updated_at"])
    return True


def publish_source_assets(ownership, paths):
    stored = stored_source_assets(ownership, paths)
    require_export_authority(ownership)
    current = current_source_job(ownership.job_id)
    if not checkpoint_attempt(
        ownership,
        {**current.checkpoint, "staged_assets": stored},
        "source_assets_staged",
    ):
        raise AttemptLost("The source operation was stopped before publication.")
