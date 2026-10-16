from pathlib import Path

from apps.ingestion.services.submissions_support.assets import calculate_checksum
from apps.processing.jobs.attempts import AttemptLost, checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .queries import current_source_job
from .storage import read_artifact, source_job_directory, write_artifact


def confined_export_path(identifier, value):
    root = source_job_directory(identifier).resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ExecutionFailure(
            FailureKind.PERMANENT, "source_export_checkpoint_invalid"
        )
    return path


def checkpointed_exports(job):
    reference = job.checkpoint.get("exports_ref")
    if not reference:
        return None
    manifest = read_artifact(job.pk, reference)
    paths = {}
    for kind, properties in manifest.items():
        path = confined_export_path(job.pk, properties["path"])
        if (
            path.stat().st_size != properties["size"]
            or calculate_checksum(path) != properties["checksum"]
        ):
            raise ExecutionFailure(
                FailureKind.PERMANENT, "source_export_checkpoint_invalid"
            )
        paths[kind] = path
    return paths


def record_export_checkpoint(ownership, paths):
    root = source_job_directory(ownership.job_id).resolve()
    manifest = {
        kind: {
            "path": str(Path(path).resolve().relative_to(root)),
            "size": path.stat().st_size,
            "checksum": calculate_checksum(path),
        }
        for kind, path in paths.items()
    }
    reference = write_artifact(ownership.job_id, manifest)
    job = current_source_job(ownership.job_id)
    if not checkpoint_attempt(
        ownership,
        {**job.checkpoint, "exports_ref": reference},
        "source_exports_generated",
    ):
        raise AttemptLost("The source operation was stopped after generation.")
