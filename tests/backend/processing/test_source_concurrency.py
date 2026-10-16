from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_processing.commands import request_source_processing
from apps.ingestion.source_processing.resolution import resolve_source_job
from apps.ingestion.source_processing.storage import write_artifact
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.requests import JobStateConflict
from source_processing_fixtures import TITLE, curated_source, execute_source_job
from test_background_job_concurrency import concurrent_calls

pytestmark = pytest.mark.django_db(transaction=True)


def request_at_barrier(arguments):
    try:
        return request_source_processing(*arguments)
    except JobStateConflict:
        return "conflict"


def test_simultaneous_identical_source_requests_share_one_operation(source_job):
    arguments = (
        source_job.requested_by,
        (source_job.pk, source_job.source_record_id),
        source_job.source_record.updated_at,
    )
    results = concurrent_calls(request_at_barrier, [arguments, arguments])
    assert results[0].pk == results[1].pk and BackgroundJob.objects.count() == 1
    assert source_job.dispatches.count() == 1


def test_different_concurrent_requests_for_one_source_accept_only_one(source_job):
    from apps.processing.jobs.controls import request_stop

    request_stop(source_job.pk, "cancel")
    arguments = [
        (
            source_job.requested_by,
            (uuid4(), source_job.source_record_id),
            source_job.source_record.updated_at,
        )
        for _ in range(2)
    ]
    results = concurrent_calls(request_at_barrier, arguments)
    assert results.count("conflict") == 1 and BackgroundJob.objects.count() == 2


def execute_at_barrier(job):
    execute_source_job(job)
    return job.state


def test_different_sources_with_one_title_cannot_silently_create_duplicate_books(
    curated_job, tmp_path
):
    actor = User.objects.create_user(
        email="parallel-source@library.test", is_staff=True
    )
    entry = SourceCatalogEntry.objects.create(
        source_url="https://source.test/books/second/", title=TITLE
    )
    other = request_source_processing(actor, (uuid4(), entry.pk), entry.updated_at)
    other.checkpoint = {
        "document_ref": write_artifact(
            other.pk, curated_source(tmp_path, entry.source_url)
        )
    }
    other.save()
    states = concurrent_calls(execute_at_barrier, [curated_job, other])
    assert sorted(states) == ["needs_attention", "succeeded"]
    assert Book.objects.count() == 1 and not UserBook.objects.exists()


def resolve_at_barrier(arguments):
    try:
        return resolve_source_job(*arguments)
    except JobStateConflict:
        return "conflict"


def test_simultaneous_source_decisions_use_one_revision(curated_job):
    Book.objects.create(title=TITLE)
    execute_source_job(curated_job)
    arguments = (
        curated_job.requested_by,
        curated_job.pk,
        {"choice": "cancel", "expected_updated_at": curated_job.updated_at},
    )
    outcomes = concurrent_calls(resolve_at_barrier, [arguments, arguments])
    assert outcomes.count("conflict") == 1
    curated_job.refresh_from_db()
    assert curated_job.state == "cancelled" and Book.objects.count() == 1
