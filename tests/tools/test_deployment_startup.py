from types import SimpleNamespace

import pytest

from tests.deployment import http_client


def simulated_time(monkeypatch, values):
    ticks = iter(values)
    monkeypatch.setattr(
        http_client,
        "time",
        SimpleNamespace(monotonic=lambda: next(ticks), sleep=lambda _seconds: None),
    )


def test_https_verification_waits_for_proxy_startup(tmp_path, monkeypatch):
    simulated_time(monkeypatch, [0, 0, 1, 2])
    statuses = iter([0, 503, 200])
    client = http_client.LocalHTTPSClient(tmp_path)
    monkeypatch.setattr(
        client, "request", lambda _path: http_client.Response(next(statuses), "", b"")
    )
    client.wait_until_ready()
    with pytest.raises(StopIteration):
        next(statuses)


def test_https_verification_fails_at_its_startup_deadline(tmp_path, monkeypatch):
    simulated_time(monkeypatch, [0, 0, 45])
    client = http_client.LocalHTTPSClient(tmp_path)
    monkeypatch.setattr(
        client, "request", lambda _path: http_client.Response(503, "", b"")
    )
    with pytest.raises(AssertionError, match="did not become ready"):
        client.wait_until_ready()
