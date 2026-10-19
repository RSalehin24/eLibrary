import pytest
from apps.common.models import AuditLog
from apps.ingestion.source_processing.defect_recovery import (
    defect_recovery_choice,
    recover_source_defect,
    recover_updated_source_defects,
)
from apps.ingestion.source_processing.issues import available_source_choices
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.processing.jobs.attempts import checkpoint_attempt, claim_attempt
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from apps.processing.jobs.requests import JobStateConflict
from apps.processing.jobs.source_defects import source_code_version
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def code_version(monkeypatch):
    version = ["1" * 64]

    def read_version(_):
        return version[0]

    monkeypatch.setattr(
        "apps.processing.jobs.source_defects.source_code_version", read_version
    )
    monkeypatch.setattr(
        "apps.ingestion.source_processing.defect_recovery.source_code_version",
        read_version,
    )
    return version


def fail_source(job, code="source_export_content_mismatch"):
    ownership = claim_attempt(job.dispatches.get(generation=job.generation).pk)
    assert ownership is not None
    checkpoint_attempt(ownership, job.checkpoint, "generating_exports")
    fail_attempt(ownership, AttemptFailure(FailureKind.PERMANENT, code))
    job.refresh_from_db()
    return job


def test_defect_fingerprint_holds_unchanged_code_and_exposes_only_safe_diagnostics(
    curated_job, code_version
):
    curated_job.checkpoint["secret"] = "PRIVATE SOURCE PATH"
    curated_job.save()
    fail_source(curated_job)
    defect = curated_job.checkpoint["source_defect"]
    assert (
        len(defect["fingerprint"]) == 64 and defect["code_version"] == code_version[0]
    )
    assert defect["stage"] == "generating_exports" and defect["code_group"] == "export"
    assert available_source_choices(curated_job) == ["cancel"]
    assert recover_source_defect(curated_job.pk) is None
    assert recover_updated_source_defects() == 0
    with pytest.raises(JobStateConflict):
        resolve_source_job(
            curated_job.requested_by,
            curated_job.pk,
            {"choice": "retry", "expected_updated_at": curated_job.updated_at},
        )
    client = APIClient()
    client.force_authenticate(curated_job.requested_by)
    response = client.get("/api/v1/manage/jobs/", {"q": defect["fingerprint"][:16]})
    assert (
        response.status_code == 200
        and response.json()["pagination"]["total_count"] == 1
    )
    assert response.json()["entries"][0]["source_defect"] == defect
    assert "PRIVATE SOURCE PATH" not in response.content.decode()


def test_code_change_retries_once_and_keeps_good_source_proof(
    curated_job, code_version
):
    curated_job.checkpoint.update(
        exports_ref="old-export",
        exports_verified=True,
        staged_assets={"epub": {}},
        publication_id="old-reader",
    )
    curated_job.save()
    fail_source(curated_job)
    previous = dict(curated_job.checkpoint)
    code_version[0] = "2" * 64
    assert defect_recovery_choice(curated_job) == "retry"
    assert recover_updated_source_defects() == 1
    curated_job.refresh_from_db()
    assert curated_job.state == "queued" and curated_job.generation == 2
    assert curated_job.checkpoint["document_ref"] == previous["document_ref"]
    assert curated_job.checkpoint["source_defect"] == previous["source_defect"]
    assert (
        not {"exports_ref", "exports_verified", "staged_assets", "publication_id"}
        & curated_job.checkpoint.keys()
    )
    assert curated_job.attempts.count() == 1 and curated_job.dispatches.count() == 2
    assert AuditLog.objects.filter(verb="source.recover_defect").count() == 1
    assert recover_source_defect(curated_job.pk) is None
    fail_source(curated_job)
    assert curated_job.state == "failed"
    assert curated_job.checkpoint["source_defect"]["code_version"] == code_version[0]
    assert recover_updated_source_defects() == 0
    assert curated_job.attempts.count() == 2


@pytest.mark.parametrize(
    "changed", ["permission", "source", "published_assets", "cancelled"]
)
def test_code_change_never_bypasses_current_authority_or_changed_inputs(
    curated_job, code_version, changed
):
    fail_source(curated_job)
    code_version[0] = "2" * 64
    if changed == "permission":
        actor = curated_job.requested_by
        actor.is_staff = False
        actor.save()
    elif changed == "source":
        entry = curated_job.source_record
        entry.title = "Updated source metadata"
        entry.save()
    elif changed == "published_assets":
        curated_job.checkpoint["assets_published"] = True
        curated_job.save()
    else:
        curated_job.state = "cancelled"
        curated_job.save()
    assert recover_source_defect(curated_job.pk) is None
    assert curated_job.dispatches.count() == 1


@pytest.mark.parametrize(
    "code",
    [
        "source_connection_unavailable",
        "source_storage_unavailable",
        "permission_revoked",
        "source_content_incomplete",
    ],
)
def test_source_availability_and_permission_failures_are_not_code_defects(
    source_job, code_version, code
):
    fail_source(source_job, code)
    assert "source_defect" not in source_job.checkpoint


def test_delivery_and_manual_epub_failures_are_not_code_defects(
    preparation_job, code_version
):
    fail_source(preparation_job, "processing_internal_error")
    assert "source_defect" not in preparation_job.checkpoint


def test_code_fingerprint_is_deterministic_and_uses_relevant_file_bytes(
    tmp_path, monkeypatch
):
    path = tmp_path / "export.py"
    path.write_text("source implementation one")
    monkeypatch.setattr(
        "apps.processing.jobs.source_defects.source_code_paths", lambda _: [path]
    )
    source_code_version.cache_clear()
    original = source_code_version("export")
    assert len(original) == 64 and source_code_version("export") == original
    path.write_text("source implementation two")
    source_code_version.cache_clear()
    assert source_code_version("export") != original
    source_code_version.cache_clear()
