from uuid import uuid4

import pytest
from apps.ingestion.source_processing.documents import write_source_result
from apps.ingestion.source_processing.layout import source_layout
from apps.ingestion.source_processing.layout_backfill import (
    apply_job_layout,
    backfill_job_layout,
)
from apps.ingestion.source_processing.summary import source_summary
from rest_framework.test import APIClient
from source_processing_fixtures import curated_source

pytestmark = pytest.mark.django_db
PATH = "/api/v1/manage/jobs/"


def layout_result(folder):
    result = curated_source(folder)
    result["source_snapshot"]["manifest"]["source_structure"] = {
        "type": "sectioned_lesson_topic_nested",
        "has_paginated_toc": True,
        "source_total_pages": 5,
        "fetched_total_pages": 3,
        "toc_incomplete": True,
    }
    return result


def client_for(job):
    client = APIClient()
    client.force_authenticate(job.requested_by)
    return client


@pytest.mark.parametrize(
    ("layout", "expected"),
    [("multi_page", True), ("complex", True), ("nested", True), ("inline", False)],
)
def test_source_layout_filters_exact_persisted_job_proof(
    source_job, tmp_path, layout, expected
):
    source_job.checkpoint = {"source_summary": source_summary(layout_result(tmp_path))}
    source_job.save()
    response = client_for(source_job).get(PATH, {"layout": layout})
    assert response.status_code == 200
    assert bool(response.json()["entries"]) is expected
    if expected:
        entry = response.json()["entries"][0]
        assert entry["source_layout"] == {
            "structure_type": "sectioned_lesson_topic_nested",
            "multi_page": True,
            "contents_pages": 5,
            "collected_contents_pages": 3,
            "contents_incomplete": True,
        }
        assert (
            not client_for(source_job)
            .get(PATH, {"layout": layout, "state": "succeeded"})
            .json()["entries"]
        )


def test_layout_is_not_inferred_from_chapter_page_count(source_job, tmp_path):
    result = layout_result(tmp_path)
    structure = result["source_snapshot"]["manifest"]["source_structure"]
    structure.update(type="flat_lessons", has_paginated_toc=False, source_total_pages=1)
    result["source_snapshot"]["pages"] *= 20
    source_job.checkpoint = {"source_summary": source_summary(result)}
    source_job.save()
    client = client_for(source_job)
    assert not client.get(PATH, {"layout": "multi_page"}).json()["entries"]
    assert not client.get(PATH, {"layout": "complex"}).json()["entries"]
    structure["source_total_pages"] = 2
    assert source_layout(result["source_snapshot"])["multi_page"] is True


@pytest.mark.parametrize(
    "structure_type", ["single_page_heading_split", "single_page_flow_no_toc"]
)
def test_inline_layout_and_saved_queue_conditions(source_job, tmp_path, structure_type):
    result = layout_result(tmp_path)
    result["source_snapshot"]["manifest"]["source_structure"].update(
        type=structure_type, has_paginated_toc=False, source_total_pages=1
    )
    source_job.checkpoint = {"source_summary": source_summary(result)}
    source_job.save()
    client = client_for(source_job)
    assert (
        client.get(PATH, {"layout": "inline"}).json()["pagination"]["total_count"] == 1
    )
    values = {
        "target": "queue",
        "operation_id": str(uuid4()),
        "name": "Inline books",
        "params": {"layout": "inline", "kind": "process_source"},
    }
    response = client.post("/api/v1/me/saved-filters/", values, format="json")
    assert response.status_code == 201 and response.json()["params"] == values["params"]


@pytest.mark.parametrize("checkpoint", [{}, {"source_summary": {"layout": None}}])
def test_unclassified_layout_is_explicit_and_source_only(
    source_job, preparation_job, checkpoint
):
    source_job.checkpoint = preparation_job.checkpoint = checkpoint
    source_job.save()
    preparation_job.save()
    response = client_for(source_job).get(PATH, {"layout": "unclassified"})
    assert response.json()["pagination"]["total_count"] == 1
    assert response.json()["entries"][0]["id"] == str(source_job.pk)
    assert response.json()["entries"][0]["source_layout"] is None


def test_layout_parameters_validate_and_preserve_queue_authorization(source_job):
    assert (
        client_for(source_job).get(PATH, {"layout": "private/input"}).status_code == 400
    )
    assert APIClient().get(PATH, {"layout": "multi_page"}).status_code == 403
    source_job.requested_by.is_staff = False
    source_job.requested_by.save()
    assert client_for(source_job).get(PATH, {"layout": "multi_page"}).status_code == 403


def test_layout_backfill_dry_run_and_apply_preserve_proof_revisions_and_history(
    source_job, tmp_path
):
    result = layout_result(tmp_path)
    source_job.checkpoint = {
        "document_ref": write_source_result(source_job.pk, result),
        "source_summary": {"verification": {"verified": False}},
        "other": "retained",
    }
    source_job.save()
    previous_revision, previous_generation = (
        source_job.updated_at,
        source_job.generation,
    )
    assert backfill_job_layout(source_job) == "would_update"
    source_job.refresh_from_db()
    assert "layout" not in source_job.checkpoint["source_summary"]
    assert backfill_job_layout(source_job, apply=True) == "updated"
    source_job.refresh_from_db()
    assert source_job.checkpoint["source_summary"]["layout"]["contents_pages"] == 5
    assert source_job.checkpoint["source_summary"]["verification"] == {
        "verified": False
    }
    assert source_job.checkpoint["other"] == "retained"
    assert (
        source_job.updated_at == previous_revision
        and source_job.generation == previous_generation
    )
    assert source_job.dispatches.count() == 1 and source_job.attempts.count() == 0
    assert backfill_job_layout(source_job, apply=True) == "unchanged"


def test_layout_backfill_never_reads_different_job_or_changed_snapshot(
    source_job, tmp_path
):
    result = layout_result(tmp_path)
    source_job.checkpoint = {"document_ref": write_source_result(source_job.pk, result)}
    source_job.save()
    source_job.checkpoint = {"document_ref": str(uuid4())}
    source_job.save(update_fields=["checkpoint"])
    assert backfill_job_layout(source_job, apply=True) == "unavailable"
    source_job.checkpoint = {}
    assert (
        apply_job_layout(source_job, source_layout(result["source_snapshot"]))
        == "changed"
    )
    source_job.refresh_from_db()
    assert "source_summary" not in source_job.checkpoint


def test_layout_backfill_skips_running_jobs(source_job, tmp_path):
    source_job.checkpoint = {
        "document_ref": write_source_result(source_job.pk, layout_result(tmp_path))
    }
    source_job.state = "running"
    source_job.save()
    assert backfill_job_layout(source_job, apply=True) == "skipped"
    assert apply_job_layout(source_job, {}) == "changed"
