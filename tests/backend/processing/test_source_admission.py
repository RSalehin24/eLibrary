from datetime import timedelta

import pytest
from apps.catalog.models import Book
from apps.ingestion.models import SourceCatalogEntry, SourceEdition
from apps.ingestion.source_processing.continuations import (
    CollectionYield,
    continue_collection,
)
from apps.ingestion.source_processing.page_cache import SourcePageCache
from apps.processing.jobs.attempts import claim_attempt
from apps.processing.jobs.failures import AttemptFailure, FailureKind, fail_attempt
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_network_availability_does_not_exhaust_processing_budget(source_job):
    source_job.max_attempts = 1
    source_job.save()
    for _ in range(5):
        source_job.refresh_from_db()
        source_job.available_at = timezone.now()
        source_job.save()
        owned = claim_attempt(
            source_job.dispatches.get(generation=source_job.generation).pk
        )
        assert owned is not None
        failed = fail_attempt(
            owned,
            AttemptFailure(FailureKind.TRANSIENT, "source_connection_unavailable"),
        )
        assert failed.state == "retry_wait" and failed.available_at > timezone.now()
    assert failed.available_at > timezone.now() + timedelta(minutes=59)
    assert source_job.attempts.count() == 5


def test_metadata_rebase_requeues_same_identity_and_preserves_attempt_history(
    source_job,
):
    owned = claim_attempt(source_job.dispatches.get().pk)
    entry = source_job.source_record
    entry.title = "Updated source title"
    entry.save()
    failed = fail_attempt(
        owned, AttemptFailure(FailureKind.PERMANENT, "source_record_changed")
    )
    assert failed.state == "queued"
    assert failed.checkpoint["source_revision"] == entry.updated_at.isoformat()
    assert failed.attempts.get().error_code == "source_record_changed"
    assert not Book.objects.exists()


def test_collection_yield_retains_ten_pages_and_resumes_without_failure(source_job):
    owned = claim_attempt(source_job.dispatches.get().pk)
    cache = SourcePageCache(owned, source_job.checkpoint)
    for index in range(10):
        cache.save(f"https://source.test/lessons/{index}/", f"<p>Chapter {index}</p>")
    with pytest.raises(CollectionYield):
        cache.read("https://source.test/lessons/next/")
    continue_collection(owned)
    source_job.refresh_from_db()
    assert source_job.state == "queued" and source_job.attempts.get().error_code == ""
    assert source_job.checkpoint["pages_fetched"] == 10
    assert SourceEdition.objects.get(operation=source_job).pages.count() == 10
    resumed = claim_attempt(
        source_job.dispatches.get(generation=source_job.generation).pk
    )
    assert (
        SourcePageCache(resumed, source_job.checkpoint).read(
            "https://source.test/lessons/0/"
        )
        == "<p>Chapter 0</p>"
    )


def test_unrecognized_source_recheck_discards_stale_text_but_preserves_identity(
    source_job,
):
    source_job.checkpoint = {
        "source_revision": source_job.source_record.updated_at.isoformat(),
        "source_url": source_job.source_record.source_url,
        "document_ref": "stale-document",
        "page_cache_ref": "stale-page",
    }
    source_job.save()
    owned = claim_attempt(source_job.dispatches.get().pk)
    failed = fail_attempt(
        owned, AttemptFailure(FailureKind.TRANSIENT, "source_description_only")
    )
    assert failed.state == "retry_wait"
    assert failed.checkpoint == {
        "source_revision": source_job.source_record.updated_at.isoformat(),
        "source_url": source_job.source_record.source_url,
    }
    assert failed.available_at > timezone.now() + timedelta(hours=5)


def test_host_circuit_opens_then_allows_only_one_probe():
    from apps.ingestion.models import SourceHostHealth
    from apps.ingestion.source_processing.host_health import (
        record_host_response,
        require_healthy_host,
    )
    from apps.processing.jobs.execution_errors import ExecutionFailure

    for _ in range(5):
        record_host_response("www.source.test", 503)
    with pytest.raises(ExecutionFailure) as closed:
        require_healthy_host("source.test")
    assert closed.value.failure.code == "source_circuit_open"
    SourceHostHealth.objects.update(open_until=timezone.now() - timedelta(seconds=1))
    require_healthy_host("source.test")
    with pytest.raises(ExecutionFailure):
        require_healthy_host("source.test")
    record_host_response("source.test", 200)
    require_healthy_host("source.test")
    assert SourceHostHealth.objects.get().failure_count == 0


def test_retry_after_accepts_seconds_and_http_date_and_rejects_invalid_values():
    from email.utils import format_datetime

    from apps.ingestion.source_processing.host_health import retry_after

    future = timezone.now().replace(microsecond=0) + timedelta(hours=1)
    assert retry_after(format_datetime(future)) == future
    assert retry_after("120") > timezone.now() + timedelta(seconds=119)
    assert retry_after("not a date") is None
    assert retry_after("-5") is None
    assert retry_after(format_datetime(future - timedelta(days=1))) is None


def test_dispatch_admission_is_bounded_and_rotates_ready_lanes(source_job, settings):
    from copy import deepcopy
    from uuid import uuid4

    from apps.processing.job_models import BackgroundJob, JobDispatch
    from apps.processing.jobs.dispatches import (
        claim_dispatches,
        record_dispatch_confirmation,
    )

    settings.CELERY_PROCESSING_CONCURRENCY = 1
    source_job.checkpoint = {"continuation": True}
    source_job.save()
    for index in range(5):
        job = BackgroundJob.objects.create(
            id=uuid4(),
            requested_by=source_job.requested_by,
            kind="process_source",
            source_record=SourceCatalogEntry.objects.create(
                source_url=f"https://source.test/books/dispatch-{index}/",
                title=f"Dispatch {index}",
            ),
            input=deepcopy(source_job.input),
            available_at=timezone.now(),
            checkpoint={},
            error_code="source_connection_unavailable" if index == 0 else "",
        )
        JobDispatch.objects.create(
            job=job, generation=job.generation, available_at=job.available_at
        )
    leases = claim_dispatches()
    assert len(leases) == 2
    jobs = [JobDispatch.objects.get(pk=lease.identifier).job for lease in leases]
    assert sorted("continuation" if job.checkpoint else "new" for job in jobs) == [
        "continuation",
        "new",
    ]
    for lease in leases:
        record_dispatch_confirmation(lease)
    assert claim_dispatches() == []
    for job in jobs:
        job.state = "succeeded"
        job.save()
    next_leases = claim_dispatches()
    assert len(next_leases) == 2
    assert any(
        JobDispatch.objects.get(pk=lease.identifier).job.error_code
        for lease in next_leases
    )


def test_rebalanced_messages_cannot_start_old_generation_and_history_remains(
    source_job,
):
    from apps.processing.jobs.source_admission import fence_source_dispatch

    old = source_job.dispatches.get()
    old.state = "published"
    old.published_at = timezone.now()
    old.save()
    assert fence_source_dispatch(source_job.pk)
    source_job.refresh_from_db()
    assert source_job.generation == old.generation + 1
    assert claim_attempt(old.pk) is None
    assert source_job.dispatches.filter(pk=old.pk, state="published").exists()
    assert claim_attempt(source_job.dispatches.get(generation=source_job.generation).pk)
    assert not fence_source_dispatch(source_job.pk)


def test_source_http_retry_after_is_persisted_and_honored(source_job):
    from apps.ingestion.source_processing.page_cache import ControlledSourceContext
    from apps.ingestion.source_processing.transport import ControlledSourceSession
    from apps.processing.jobs.execution_errors import ExecutionFailure
    from source_transport_fixture import FixtureAdapter, fixture_request_slot

    owned = claim_attempt(source_job.dispatches.get().pk)
    cache = SourcePageCache(owned, source_job.checkpoint)
    with ControlledSourceSession(cache.boundary, fixture_request_slot) as session:
        session.mount(
            "https://", FixtureAdapter([(429, {"Retry-After": "3600"}, b"unavailable")])
        )
        with pytest.raises(ExecutionFailure) as unavailable:
            ControlledSourceContext(session, cache).fetch_html(
                source_job.source_record.source_url
            )
    failed = fail_attempt(owned, unavailable.value.failure)
    assert (
        failed.state == "retry_wait"
        and failed.available_at > timezone.now() + timedelta(minutes=59)
    )
    assert not failed.checkpoint.get("pages_fetched")


def test_page_cache_uses_disk_budget_separately_from_individual_document_limit(
    source_job,
):
    from apps.ingestion.source_processing.page_cache import SourcePageCache

    owned = claim_attempt(source_job.dispatches.get().pk)
    cache = SourcePageCache(
        owned, {**source_job.checkpoint, "cache_bytes": 70 * 1024 * 1024}
    )
    url = source_job.source_record.source_url
    cache.save(url, "<p>Reading page</p>")
    size = cache.size
    cache.save(url, "<p>Replacement page</p>")
    assert cache.size == size + len("Replacement") - len("Reading")
    assert len(cache.pages) == 1
    assert cache.read(url) == "<p>Replacement page</p>"


def test_older_page_cache_gets_durable_evidence_once_when_resumed(source_job):
    from hashlib import sha256

    from apps.ingestion.models import SourceEditionPage
    from apps.ingestion.source_processing.storage import write_artifact

    page = "<p>Pinned reading page</p>"
    url = source_job.source_record.source_url
    reference = write_artifact(source_job.pk, page)
    checkpoint = {
        **source_job.checkpoint,
        "page_cache_ref": write_artifact(source_job.pk, {url: reference}),
    }
    owned = claim_attempt(source_job.dispatches.get().pk)
    cache = SourcePageCache(owned, checkpoint)
    proof = SourceEditionPage.objects.get()
    assert proof.content_hash == sha256(page.encode()).hexdigest()
    SourcePageCache(owned, checkpoint)
    assert SourceEditionPage.objects.get().updated_at == proof.updated_at
    cache.save(url, "<p>Updated page</p>")
    proof.refresh_from_db()
    assert proof.position == 0
