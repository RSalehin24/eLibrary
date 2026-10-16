from datetime import timedelta
from unittest.mock import Mock

import pytest
from apps.ingestion.models import SourceRequestWindow
from apps.ingestion.source_processing.pacing import (
    reserve_source_slot,
    wait_for_source_slot,
)
from apps.ingestion.source_processing.transport import ControlledSourceSession
from apps.processing.jobs.attempts import AttemptLost
from apps.processing.jobs.execution_errors import ExecutionFailure
from django.utils import timezone
from source_transport_fixture import FixtureAdapter
from test_background_job_concurrency import concurrent_calls

pytestmark = pytest.mark.django_db


def test_source_host_aliases_share_one_request_window(settings):
    settings.SOURCE_REQUEST_INTERVAL_SECONDS = "2"
    assert reserve_source_slot("source.test") == 0
    assert 0 < reserve_source_slot("www.source.test") <= 2
    assert reserve_source_slot("other.test") == 0
    assert SourceRequestWindow.objects.count() == 2


def test_expired_windows_accept_without_accumulating_a_backlog(settings):
    settings.SOURCE_REQUEST_INTERVAL_SECONDS = "2"
    SourceRequestWindow.objects.create(
        host="source.test", available_at=timezone.now() - timedelta(days=3)
    )
    assert reserve_source_slot("source.test") == 0
    assert reserve_source_slot("source.test") > 0


@pytest.mark.parametrize("value", ["invalid", 0, -1, "NaN", "Infinity", 61])
def test_invalid_pacing_configuration_fails_without_allocating_a_slot(settings, value):
    settings.SOURCE_REQUEST_INTERVAL_SECONDS = value
    with pytest.raises(ExecutionFailure, match="source_request_interval_invalid"):
        reserve_source_slot("source.test")
    assert not SourceRequestWindow.objects.exists()


def test_waiting_checks_cooperative_stops_between_bounded_sleeps(monkeypatch):
    reserve = Mock(side_effect=[2, 1, 0])
    sleeping, boundary = Mock(), Mock()
    monkeypatch.setattr(
        "apps.ingestion.source_processing.pacing.reserve_source_slot", reserve
    )
    monkeypatch.setattr("apps.ingestion.source_processing.pacing.sleep", sleeping)
    wait_for_source_slot("source.test", boundary)
    assert [call.args for call in sleeping.call_args_list] == [(1,), (1,)]
    assert boundary.call_count == 2


def test_a_stop_during_wait_never_retries_or_fetches(monkeypatch):
    reserve = Mock(return_value=2)
    monkeypatch.setattr(
        "apps.ingestion.source_processing.pacing.reserve_source_slot", reserve
    )
    monkeypatch.setattr("apps.ingestion.source_processing.pacing.sleep", Mock())
    with pytest.raises(AttemptLost):
        wait_for_source_slot("source.test", Mock(side_effect=AttemptLost("stopped")))
    assert reserve.call_count == 1


def test_every_allowed_redirect_passes_through_the_shared_pacer(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    pacing = Mock()
    adapter = FixtureAdapter(
        [(302, {"Location": "/books/next/"}, b""), (200, {}, b"ok")]
    )
    with ControlledSourceSession(Mock(), pacing) as session:
        session.mount("https://", adapter)
        session.get("https://source.test/books/start/")
    assert pacing.call_count == len(adapter.calls) == 2
    assert all(call.args[0] == "source.test" for call in pacing.call_args_list)


@pytest.mark.django_db(transaction=True)
def test_concurrent_workers_cannot_claim_the_same_host_slot(settings):
    settings.SOURCE_REQUEST_INTERVAL_SECONDS = "2"
    delays = concurrent_calls(reserve_source_slot, ["source.test", "www.source.test"])
    assert sum(delay == 0 for delay in delays) == 1
    assert SourceRequestWindow.objects.count() == 1
