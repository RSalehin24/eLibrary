from unittest.mock import Mock

import pytest
import requests
from apps.ingestion.source_processing.transport import ControlledSourceSession
from apps.processing.jobs.execution_errors import ExecutionFailure
from source_transport_fixture import FixtureAdapter, fixture_request_slot


@pytest.fixture
def source_session(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    return ControlledSourceSession(Mock(), fixture_request_slot)


def test_transport_enforces_verified_tls_bounded_timeouts_and_preserves_bengali(
    source_session,
):
    adapter = FixtureAdapter([(200, {}, "বাংলা উৎসের লেখা".encode())])
    source_session.mount("https://", adapter)
    response = source_session.get("https://source.test/books/example/")
    assert response.content.decode() == "বাংলা উৎসের লেখা"
    options = adapter.calls[0][1]
    assert options["verify"] is True and options["timeout"] == (10, 60)
    assert source_session.trust_env is False
    source_session.before_request.assert_called_once()


@pytest.mark.parametrize(
    "url",
    [
        "http://source.test/books/example/",
        "https://evil.test/books/example/",
        "https://user:secret@source.test/books/example/",
        "https://source.test:444/books/example/",
        "https://source.test/books/example/?token=secret",
        "https://source.test/books/example/#fragment",
    ],
)
def test_disallowed_requests_never_reach_the_transport(source_session, url):
    adapter = FixtureAdapter([])
    source_session.mount("https://", adapter)
    source_session.mount("http://", adapter)
    with pytest.raises(ExecutionFailure) as error:
        source_session.get(url)
    assert error.value.failure.code == "source_url_not_allowed" and adapter.calls == []


def test_redirects_to_another_host_are_denied_before_the_second_request(source_session):
    adapter = FixtureAdapter([(302, {"Location": "https://evil.test/private/"}, b"")])
    source_session.mount("https://", adapter)
    with pytest.raises(ExecutionFailure) as error:
        source_session.get("https://source.test/books/example/")
    assert (
        error.value.failure.code == "source_url_not_allowed" and len(adapter.calls) == 1
    )


def test_oversized_source_response_fails_with_a_non_sensitive_code(
    source_session, monkeypatch
):
    monkeypatch.setattr(
        "apps.ingestion.source_processing.transport.MAX_RESPONSE_BYTES", 10
    )
    adapter = FixtureAdapter([(200, {}, b"x" * 11)])
    source_session.mount("https://", adapter)
    with pytest.raises(ExecutionFailure) as error:
        source_session.get("https://source.test/books/example/")
    assert error.value.failure.code == "source_response_too_large"


def test_connection_failures_do_not_expose_provider_details(source_session):
    adapter = FixtureAdapter(
        [requests.ConnectionError("synthetic private provider detail")]
    )
    source_session.mount("https://", adapter)
    with pytest.raises(ExecutionFailure) as error:
        source_session.get("https://source.test/books/example/")
    assert error.value.failure.kind == "transient" and "private provider" not in str(
        error.value
    )


def test_source_configuration_is_required_before_transport_is_opened(settings):
    settings.SOURCE_SITE_HOST = ""
    with pytest.raises(ExecutionFailure) as error:
        ControlledSourceSession(Mock())
    assert error.value.failure.code == "source_configuration_missing"


def test_another_configured_website_cannot_be_added_as_a_fallback(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = ["different.test"]
    with pytest.raises(ExecutionFailure) as error:
        ControlledSourceSession(Mock())
    assert error.value.failure.code == "source_configuration_invalid"


def test_primary_site_www_alias_is_the_only_permitted_fallback(settings):
    settings.SOURCE_SITE_HOST = "www.source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = ["source.test"]
    from apps.ingestion.source_processing.policy import source_hosts

    assert source_hosts() == frozenset({"source.test", "www.source.test"})
