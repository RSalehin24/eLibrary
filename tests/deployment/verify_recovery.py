import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from compose_client import IsolatedCompose
from http_client import LocalHTTPSClient
from verify_platform import verify_public, verify_reading


def wait_for(check, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(1)
    raise AssertionError("The isolated service did not recover within its deadline.")


@contextmanager
def stopped(compose, *services):
    try:
        compose.call("stop", "--timeout", "15", *services)
        yield
    finally:
        compose.call("start", *services)


def successful_job(compose, identifier):
    job = compose.probe("snapshot", identifier)
    assert job["state"] not in {"failed", "cancelled"}, "The recovery job failed."
    return job if job["state"] == "succeeded" else None


def verify_broker_recovery(compose):
    with stopped(compose, "rabbitmq"):
        job = compose.probe("create")

        def pending_failure():
            status = compose.probe("snapshot", job["id"])
            return status["dispatch_pending"] and status["dispatch_failures"] > 0

        wait_for(pending_failure)
    completed = wait_for(lambda: successful_job(compose, job["id"]))
    assert completed["attempt_count"] == 1 and completed["checkpoint_saved"]
    compose.probe("duplicate", job["id"])
    time.sleep(3)
    assert compose.probe("snapshot", job["id"])["attempt_count"] == 1
    print("Broker outage, confirmed retry, and duplicate delivery passed.", flush=True)


def verify_interrupted_attempt(compose):
    with stopped(compose, "dispatcher", "processing-worker"):
        job = compose.probe("interrupted")
        assert job["state"] == "running" and job["checkpoint_saved"]
    completed = wait_for(lambda: successful_job(compose, job["id"]))
    assert completed["attempt_count"] == 2 and completed["checkpoint_saved"]
    print("Persisted stale attempt and checkpoint recovery passed.", flush=True)


def verify_active_worker_interruption(compose):
    job = compose.probe("create_interruptible")
    active = wait_for(lambda: preparing_job(compose, job["id"]))
    assert active["attempt_count"] == 1
    try:
        compose.call("kill", "--signal", "SIGKILL", "processing-worker")
    finally:
        compose.call("start", "processing-worker")
    completed = wait_for(lambda: successful_job(compose, job["id"]), seconds=240)
    assert completed["attempt_count"] == 2 and completed["checkpoint_saved"]
    assert completed["prepared_publications"] == 1
    compose.probe("duplicate", job["id"])
    time.sleep(3)
    assert compose.probe("snapshot", job["id"])["attempt_count"] == 2
    print(
        "Active preparation worker SIGKILL, lease recovery, and duplicate replay passed.",
        flush=True,
    )


def preparing_job(compose, identifier):
    job = compose.probe("snapshot", identifier)
    assert job["state"] not in {"failed", "succeeded"}, (
        "The interruption window was missed."
    )
    return job if job["active_stage"] == "preparing" else None


def verify_broker_replacement(compose):
    with stopped(compose, "processing-worker"):
        job = compose.probe("create")
        wait_for(lambda: compose.probe("snapshot", job["id"])["dispatch_published"])
        compose.call(
            "up", "-d", "--no-build", "--no-deps", "--force-recreate", "rabbitmq"
        )
        wait_for(lambda: broker_is_ready(compose))
        pending = compose.probe("snapshot", job["id"])
        assert pending["attempt_count"] == 0 and pending["dispatch_published"]
    completed = wait_for(lambda: successful_job(compose, job["id"]), seconds=30)
    assert completed["attempt_count"] == 1
    print(
        "A confirmed queued task survived RabbitMQ container replacement.", flush=True
    )


def broker_is_ready(compose):
    values = json.loads(compose.call("ps", "--format", "json", "rabbitmq"))
    return values["Health"] == "healthy"


def verify_cache_recovery(compose, fixture):
    client = LocalHTTPSClient(compose.directory)
    chapter = verify_reading(client, fixture)
    anonymous = LocalHTTPSClient(compose.directory)
    token = anonymous.request("/api/v1/auth/session/").json()["csrf_token"]
    anonymous.headers.update(
        {"X-CSRFToken": token, "Origin": "https://library.example.test:18443"}
    )
    account = fixture["reading_reader"]
    with stopped(compose, "redis"):
        assert client.request(chapter).status == 200
        assert client.request("/api/v1/auth/session/").json()["authenticated"]
        response = anonymous.request(
            "/api/v1/auth/login/",
            {"email": account["email"], "password": account["password"]},
        )
        assert (
            response.status == 503
            and response.json()["code"] == "rate_limits_unavailable"
        )
    wait_for(lambda: anonymous.request("/api/v1/health/ready/").status == 200)
    response = anonymous.request(
        "/api/v1/auth/login/",
        {"email": account["email"], "password": account["password"]},
    )
    assert response.status == 200, (
        "Authentication did not recover after Redis restarted."
    )
    print(
        "Cache outage preserved sessions/books and failed rate-limited login with 503; recovery passed.",
        flush=True,
    )


def verify_container_replacement(compose, fixture):
    client = LocalHTTPSClient(compose.directory)
    for service, path in (
        ("api", "/api/v1/health/ready/"),
        ("frontend", f"/books/{fixture['public_book']['slug']}/"),
    ):
        compose.call("up", "-d", "--no-build", "--no-deps", "--force-recreate", service)
        wait_for(lambda path=path: client.request(path).status == 200)
    verify_public(client, fixture)
    verify_reading(client, fixture)
    print(
        "API/frontend replacement recovered through the running proxy without a reload.",
        flush=True,
    )


def main():
    directory = Path(os.environ["DEPLOYMENT_TEST_DIRECTORY"])
    compose = IsolatedCompose(directory)
    compose.prepare_scripts()
    fixture = json.loads((directory / "fixture.json").read_text())
    verify_broker_recovery(compose)
    verify_broker_replacement(compose)
    verify_interrupted_attempt(compose)
    verify_active_worker_interruption(compose)
    verify_cache_recovery(compose, fixture)
    verify_container_replacement(compose, fixture)


if __name__ == "__main__":
    main()
