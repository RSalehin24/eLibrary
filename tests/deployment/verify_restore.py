import hashlib
import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

from compose_client import IsolatedCompose
from http_client import LocalHTTPSClient
from verify_platform import verify_public, verify_reading
from verify_recovery import stopped, successful_job, wait_for

WRITERS = ("api", "dispatcher", "scheduler", "processing-worker", "delivery-worker")
SOURCE_SERVICES = (*WRITERS, "frontend", "proxy", "rabbitmq", "redis", "postgres")


def private_file(path, contents):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(contents)


def save_progress(client, fixture):
    client.authenticate(fixture["reading_reader"])
    slug = fixture["reading_book"]["slug"]
    launched = client.request(f"/api/v1/reading/books/{slug}/launch/", {}).json()
    path = f"/api/v1/reading/sessions/{launched['id']}/progress/"
    response = client.request(
        path,
        {"last_location": "chapter-1.xhtml", "progress_percent": 42.5},
        method="PUT",
    )
    assert response.status == 200


def prepare_snapshot(compose, fixture):
    compose.prepare_scripts()
    save_progress(LocalHTTPSClient(compose.directory), fixture)
    with stopped(compose, "dispatcher", "processing-worker"):
        job = compose.probe("paused")
        assert job["state"] == "paused" and job["checkpoint_saved"]
    return job["id"]


def capture_backup(compose, directory):
    with stopped(compose, *WRITERS):
        database = compose.call(
            "exec",
            "-T",
            "postgres",
            "pg_dump",
            "--username=library",
            "--dbname=library",
            "--format=custom",
            "--no-owner",
            "--no-acl",
        )
        storage = compose.call(
            "run",
            "--no-deps",
            "-T",
            "initialize",
            "python",
            "-c",
            "import sys,tarfile; archive=tarfile.open(fileobj=sys.stdout.buffer, mode='w|'); archive.add('/data/media',arcname='media'); archive.add('/data/runtime',arcname='runtime'); archive.close()",
        )
    private_file(directory / "database.dump", database)
    private_file(directory / "storage.tar", storage)
    manifest = {
        name: {"sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
        for name, value in (("database.dump", database), ("storage.tar", storage))
    }
    private_file(directory / "checksums.json", json.dumps(manifest, indent=2).encode())
    print(
        "Consistent database/media/runtime backup captured with private files and checksums.",
        flush=True,
    )


def restore_configuration(source, directory):
    name = f"elibrary-platform-test-restore-{uuid4().hex[:8]}"
    lines = (source.directory / "platform.env").read_text().splitlines(keepends=True)
    assert sum(line.startswith("COMPOSE_PROJECT_NAME=") for line in lines) == 1
    values = "".join(
        f"COMPOSE_PROJECT_NAME='{name}'\n"
        if line.startswith("COMPOSE_PROJECT_NAME=")
        else line
        for line in lines
    )
    private_file(directory / "platform.env", values.encode())
    shutil.copy2(source.directory / "fixture.json", directory / "fixture.json")
    (directory / "tls").mkdir(mode=0o700)
    shutil.copy2(
        source.directory / "tls/fullchain.pem", directory / "tls/fullchain.pem"
    )
    return IsolatedCompose(directory)


def restore_data(compose):
    compose.call("up", "-d", "--wait", "postgres")
    compose.call(
        "exec",
        "-T",
        "postgres",
        "pg_restore",
        "--username=library",
        "--dbname=library",
        "--no-owner",
        "--no-acl",
        "--exit-on-error",
        data=(compose.directory / "database.dump").read_bytes(),
    )
    compose.call(
        "run",
        "--no-deps",
        "-T",
        "initialize",
        "python",
        "-c",
        "import sys,tarfile; archive=tarfile.open(fileobj=sys.stdin.buffer,mode='r|'); archive.extractall('/data',filter='data'); archive.close()",
        data=(compose.directory / "storage.tar").read_bytes(),
    )
    print(
        "Backup restored into a separate empty project and storage volumes.", flush=True
    )


def verify_restored_progress(client, fixture):
    client.authenticate(fixture["reading_reader"])
    slug = fixture["reading_book"]["slug"]
    launched = client.request(f"/api/v1/reading/books/{slug}/launch/", {})
    assert launched.status == 200
    progress = launched.json()["reading_progress"]
    assert progress == {"last_location": "chapter-1.xhtml", "progress_percent": 42.5}


def verify_restored_job(compose, client, job_id):
    compose.prepare_scripts()
    job = compose.probe("snapshot", job_id)
    assert job["state"] == "paused" and job["checkpoint_saved"]
    fixture = json.loads((compose.directory / "fixture.json").read_text())
    client.authenticate(fixture["administrator"])
    response = client.request(
        f"/api/v1/manage/jobs/{job_id}/",
        {"action": "resume", "expected_updated_at": job["updated_at"]},
    )
    assert response.status == 202
    completed = wait_for(lambda: successful_job(compose, job_id))
    assert completed["attempt_count"] == 2 and completed["checkpoint_saved"]


def verify_restored_stack(source, restored, fixture, job_id):
    with stopped(source, *SOURCE_SERVICES):
        try:
            restored.call("up", "-d", "--no-build")
            client = LocalHTTPSClient(restored.directory)
            wait_for(lambda: client.request("/api/v1/health/ready/").status == 200)
            verify_public(client, fixture)
            verify_reading(client, fixture)
            verify_restored_progress(client, fixture)
            verify_restored_job(restored, client, job_id)
        finally:
            restored.call("stop", "--timeout", "20")
    wait_for(
        lambda: (
            LocalHTTPSClient(source.directory).request("/api/v1/health/ready/").status
            == 200
        )
    )
    source.prepare_scripts()
    assert source.probe("snapshot", job_id)["state"] == "paused"
    print(
        "Restore checks passed: sessions, permissions, protected bytes, progress, and paused-job resume; source data preserved.",
        flush=True,
    )


def main():
    directory = Path(os.environ["DEPLOYMENT_TEST_DIRECTORY"])
    source = IsolatedCompose(directory)
    fixture = json.loads((directory / "fixture.json").read_text())
    job_id = prepare_snapshot(source, fixture)
    backup = directory / f"restore-{uuid4().hex[:8]}"
    backup.mkdir(mode=0o700)
    capture_backup(source, backup)
    restored = restore_configuration(source, backup)
    restore_data(restored)
    verify_restored_stack(source, restored, fixture, job_id)


if __name__ == "__main__":
    main()
