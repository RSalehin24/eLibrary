import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings

from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .policy import MAX_DOCUMENT_BYTES


def source_job_directory(identifier):
    root = Path(settings.RUNTIME_STORAGE_DIR) / "source-work"
    directory = root / str(UUID(str(identifier)))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory


def artifact_path(identifier, reference):
    return source_job_directory(identifier) / f"{UUID(str(reference))}.json"


def write_artifact(identifier, value):
    data = json.dumps(value, ensure_ascii=False).encode()
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_document_too_large")
    reference = uuid4()
    path = artifact_path(identifier, reference)
    with path.with_suffix(".tmp").open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    path.with_suffix(".tmp").replace(path)
    return str(reference)


def read_artifact(identifier, reference):
    try:
        with artifact_path(identifier, reference).open("rb") as handle:
            data = handle.read(MAX_DOCUMENT_BYTES + 1)
        if len(data) > MAX_DOCUMENT_BYTES:
            raise ValueError("Checkpoint size exceeded.")
        return json.loads(data)
    except (OSError, ValueError):
        raise ExecutionFailure(
            FailureKind.PERMANENT, "source_checkpoint_invalid"
        ) from None
