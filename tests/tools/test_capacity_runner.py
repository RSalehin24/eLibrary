import json
import subprocess
from types import SimpleNamespace

import pytest

from tests.performance import run_capacity


def test_capacity_container_keeps_tls_checks_and_private_files_scoped(tmp_path):
    directory = tmp_path / "fixture"
    artifacts = tmp_path / "artifacts"
    command = run_capacity.container_command(directory, artifacts, "isolated-network")
    assert "--pull" in command and command[command.index("--pull") + 1] == "never"
    assert run_capacity.K6_IMAGE in command
    assert "SSL_CERT_FILE=/private/fullchain.pem" in command
    assert "--include-system-env-vars=false" in command
    assert command[command.index("--log-output") + 1] == "none"
    assert not any("platform.env" in item or "privkey.pem" in item for item in command)
    assert not any("insecure-skip-tls-verify" in item for item in command)
    mounts = [
        command[index + 1] for index, item in enumerate(command) if item == "--mount"
    ]
    assert len(mounts) == 5 and sum(item.endswith(",readonly") for item in mounts) == 4


def test_capacity_host_mapping_uses_only_the_isolated_proxy_network(monkeypatch):
    stack = SimpleNamespace(call=lambda *_args: b"isolated-proxy\n")
    configuration = {"networks": {"outbound": {"name": "isolated-outbound"}}}
    monkeypatch.setattr(
        run_capacity,
        "docker_output",
        lambda *_args: '{"isolated-outbound":{"IPAddress":"172.20.0.3"}}',
    )
    assert run_capacity.proxy_address(stack, configuration) == (
        "isolated-outbound",
        "172.20.0.3",
    )
    monkeypatch.setattr(
        run_capacity,
        "docker_output",
        lambda *_args: '{"isolated-outbound":{"IPAddress":"foreign.test"}}',
    )
    with pytest.raises(ValueError):
        run_capacity.proxy_address(stack, configuration)


def test_capacity_docker_failure_does_not_expose_diagnostics(monkeypatch):
    monkeypatch.setattr(
        run_capacity.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            [], 1, stdout=b"", stderr=b"private-credential"
        ),
    )
    with pytest.raises(RuntimeError, match="Docker capacity command failed") as failure:
        run_capacity.docker_output("inspect", "synthetic")
    assert "private-credential" not in str(failure.value)


def test_timed_out_capacity_run_stops_its_container(monkeypatch, tmp_path):
    calls = []
    process = SimpleNamespace(
        poll=lambda: None, wait=lambda **_kwargs: calls.append("wait")
    )
    monkeypatch.setattr(
        run_capacity.subprocess, "Popen", lambda *_args, **_kwargs: process
    )
    ticks = iter([0, 2])
    monkeypatch.setattr(run_capacity.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(run_capacity, "docker_output", lambda *args: calls.append(args))
    invocation = {
        "command": ["synthetic"],
        "timeout": 1,
        "container_name": "isolated-capacity",
    }
    with pytest.raises(TimeoutError):
        run_capacity.execute(invocation, SimpleNamespace(), tmp_path)
    assert calls == [("stop", "--time", "5", "isolated-capacity"), "wait"]


def test_capacity_success_requires_a_complete_successful_summary(tmp_path):
    path = tmp_path / "summary.json"
    metrics = {
        "checks": {"values": {"rate": 1}},
        "http_req_failed": {"values": {"rate": 0}},
        "iterations": {"values": {"count": 1}},
        "public_latency_ms": {"values": {"count": 3}},
        "reading_latency_ms": {"values": {"count": 1}},
    }
    path.write_text(json.dumps({"metrics": metrics}))
    run_capacity.validate_summary(path)
    metrics["checks"]["values"]["rate"] = 0.5
    path.write_text(json.dumps({"metrics": metrics}))
    with pytest.raises(RuntimeError, match="completed successful workload"):
        run_capacity.validate_summary(path)


def test_capacity_missing_or_empty_summary_is_a_failure(tmp_path):
    path = tmp_path / "summary.json"
    with pytest.raises(RuntimeError, match="completed successful workload"):
        run_capacity.validate_summary(path)
    path.write_text('{"metrics": {}}')
    with pytest.raises(RuntimeError, match="completed successful workload"):
        run_capacity.validate_summary(path)
