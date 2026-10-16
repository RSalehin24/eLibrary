from unittest.mock import Mock

import pytest
from apps.ingestion.source_processing.page_cache import (
    ControlledSourceContext,
    SourcePageCache,
)
from apps.ingestion.source_processing.storage import read_artifact
from apps.processing.jobs.attempts import AttemptLost, claim_attempt
from apps.processing.jobs.controls import request_stop, resume_job
from source_processing_fixtures import SOURCE_URL

pytestmark = pytest.mark.django_db


def test_page_checkpoints_resume_without_fetching_saved_html(source_job):
    ownership = claim_attempt(source_job.dispatches.get().pk)
    cache = SourcePageCache(ownership, {})
    cache.save(SOURCE_URL, "<p>আগের সংগৃহীত পাতা</p>")
    request_stop(source_job.pk, "pause")
    with pytest.raises(AttemptLost):
        cache.read(SOURCE_URL)
    source_job.refresh_from_db()
    assert source_job.state == "paused" and source_job.checkpoint["pages_fetched"] == 1
    resume_job(source_job.pk)
    source_job.refresh_from_db()
    ownership = claim_attempt(
        source_job.dispatches.get(generation=source_job.generation).pk
    )
    resumed = SourcePageCache(ownership, source_job.checkpoint)
    session = Mock()
    context = ControlledSourceContext(session, resumed)
    assert "আগের সংগৃহীত পাতা" in str(context.fetch_soup(SOURCE_URL, kind="landing"))
    session.get.assert_not_called()


def test_cancelled_and_stale_attempts_cannot_replace_the_committed_checkpoint(
    source_job,
):
    ownership = claim_attempt(source_job.dispatches.get().pk)
    cache = SourcePageCache(ownership, {})
    cache.save(SOURCE_URL, "<p>অক্ষত পাতা</p>")
    request_stop(source_job.pk, "cancel")
    with pytest.raises(AttemptLost):
        cache.read(SOURCE_URL)
    source_job.refresh_from_db()
    original = dict(source_job.checkpoint)
    with pytest.raises(AttemptLost):
        cache.save("https://source.test/books/another/", "<p>বাতিল হওয়া লেখার পাতা</p>")
    source_job.refresh_from_db()
    assert source_job.state == "cancelled" and source_job.checkpoint == original
    pages = read_artifact(source_job.pk, original["page_cache_ref"])
    assert list(pages) == [SOURCE_URL]


def test_current_authority_is_checked_at_each_page_boundary(source_job):
    ownership = claim_attempt(source_job.dispatches.get().pk)
    cache = SourcePageCache(ownership, {})
    actor = source_job.requested_by
    actor.is_staff = False
    actor.save()
    from apps.processing.jobs.execution_errors import ExecutionFailure

    with pytest.raises(ExecutionFailure) as error:
        cache.read(SOURCE_URL)
    assert error.value.failure.code == "permission_revoked"
