from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from rest_framework import serializers

from apps.processing.job_models import JobAttempt

SOURCE_DEFECT_CODES = {
    "processing_internal_error": "source",
    "source_export_content_mismatch": "export",
    "source_exports_missing": "export",
    "invalid_epub": "reader",
}


def source_code_paths(group):
    root = Path(__file__).resolve().parents[2]
    paths = list((root / "ingestion/pipeline").rglob("*.py"))
    source_root = root / "ingestion/source_processing"
    paths.extend(source_root.rglob("*.py"))
    if group == "source":
        paths.extend((root / "processing/jobs").rglob("*.py"))
    if group == "reader":
        paths.extend((root / "access/reading").rglob("*.py"))
    if group == "export":
        paths = [
            path
            for path in paths
            if "export" in path.stem or "epub" in str(path) or "html" in path.stem
        ]
        paths.append(root / "processing/source.py")
    return sorted(paths)


@lru_cache(maxsize=3)
def source_code_version(group):
    digest = sha256()
    for path in source_code_paths(group):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def record_source_defect(job, failure):
    if job.kind != "process_source" or failure.code not in SOURCE_DEFECT_CODES:
        return False
    group = SOURCE_DEFECT_CODES[failure.code]
    stage = JobAttempt.objects.get(pk=job.active_attempt_id).stage
    version = source_code_version(group)
    fingerprint = sha256(f"{failure.code}:{stage}:{version}".encode()).hexdigest()
    job.checkpoint = {
        **job.checkpoint,
        "source_defect": {
            "fingerprint": fingerprint,
            "code_version": version,
            "code_group": group,
            "error_code": failure.code,
            "stage": stage,
        },
    }
    return True


def source_defect_waits_for_code(job):
    defect = job.checkpoint.get("source_defect")
    if not defect or job.error_code not in SOURCE_DEFECT_CODES:
        return False
    group = SOURCE_DEFECT_CODES[job.error_code]
    return defect.get("code_version") == source_code_version(group)


class SourceDefectSerializer(serializers.Serializer):
    fingerprint = serializers.RegexField(r"^[0-9a-f]{64}$")
    code_version = serializers.RegexField(r"^[0-9a-f]{64}$")
    code_group = serializers.ChoiceField(choices=["source", "export", "reader"])
    error_code = serializers.CharField(max_length=64)
    stage = serializers.CharField(max_length=64, allow_blank=True)
