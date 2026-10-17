from pathlib import Path
from shutil import copyfile

from apps.catalog.models import GeneratedAssetType
from apps.ingestion.pipeline.curated_export import curated_document_to_legacy_payload
from apps.ingestion.services.submissions_support.assets import (
    candidate_asset_paths,
)
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind
from apps.processing.source import generate_exports

from .export_checkpoint import checkpointed_exports, record_export_checkpoint
from .guards import require_export_authority
from .queries import current_source_job
from .regeneration_exports import regenerated_export_payload
from .storage import source_job_directory


def export_payload(ownership, result):
    payload = curated_document_to_legacy_payload(result["document"])
    root = source_job_directory(ownership.job_id)
    folder = root / str(ownership.attempt_id) / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    cover = payload.get("cover", "")
    if cover:
        path = (Path(payload["output_folder"]) / cover).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            raise ExecutionFailure(
                FailureKind.PERMANENT, "source_cover_path_invalid"
            ) from None
        copyfile(path, folder / path.name)
        payload["cover"] = path.name
    payload["output_folder"] = str(folder)
    if current_source_job(ownership.job_id).input.get("regenerate_book"):
        payload = regenerated_export_payload(
            require_export_authority(ownership), payload
        )
    return payload


def generated_source_assets(ownership, result):
    require_export_authority(ownership)
    cached = checkpointed_exports(current_source_job(ownership.job_id))
    if cached is not None:
        return cached
    payload = export_payload(ownership, result)
    generate_exports(payload)
    paths = candidate_asset_paths(payload)
    required = [GeneratedAssetType.HTML, GeneratedAssetType.EPUB]
    if any(not paths.get(kind) or not paths[kind].is_file() for kind in required):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_exports_missing")
    available = {kind: path for kind, path in paths.items() if path and path.is_file()}
    record_export_checkpoint(ownership, available)
    return available
