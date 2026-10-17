from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .storage import read_artifact, write_artifact

DOCUMENT_PARTS = ("document", "source_snapshot", "projection")
PARTITIONED_FORMAT = "source-result-parts-v1"


def write_source_result(identifier, result):
    # Each independently bounded part avoids multiplying a large book into one JSON file.
    parts = {
        key: write_artifact(identifier, result[key]) for key in DOCUMENT_PARTS
    }
    return write_artifact(
        identifier,
        {
            "artifact_format": PARTITIONED_FORMAT,
            "parts": parts,
            "status": result["status"],
            "validation": result["validation"],
        },
    )


def read_source_result(identifier, reference):
    result = read_artifact(identifier, reference)
    if result.get("artifact_format") != PARTITIONED_FORMAT:
        return result
    parts = result.get("parts", {})
    if set(parts) != set(DOCUMENT_PARTS):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_checkpoint_invalid")
    return {
        **{key: read_artifact(identifier, parts[key]) for key in DOCUMENT_PARTS},
        "status": result["status"],
        "validation": result["validation"],
    }
