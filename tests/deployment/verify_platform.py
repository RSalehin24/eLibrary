import json
import os
import re
import time
from pathlib import Path
from uuid import uuid4

from http_client import LocalHTTPSClient


def verify_public(client, fixture):
    for path in (
        "/api/v1/health/live/",
        "/api/v1/health/ready/",
        "/manifest.webmanifest",
        "/sitemap.xml",
    ):
        assert client.request(path).status == 200, f"Unavailable public path: {path}"
    book = fixture["public_book"]
    response = client.request(f"/books/{book['slug']}/")
    assert response.status == 200 and book["title"].encode() in response.body
    assert b'lang="bn"' in response.body and b"application/ld+json" in response.body
    assert b"https://library.example.test:18443/books/" in response.body
    verify_public_assets(client, response.body)
    for path in (
        "/_protected/",
        "/media/protected/",
        "/api/auth/demo-login/",
        "/api/catalog/books/",
    ):
        assert client.request(path).status == 404, f"Private route exposed: {path}"


def verify_public_assets(client, html):
    match = re.search(rb'src="(/_next/static/[^"?]+\.js)"', html)
    assert match, "The server-rendered page has no script asset."
    asset = client.request(match[1].decode())
    assert asset.status == 200 and "immutable" in asset.headers
    missing = client.request("/_next/static/missing-test-asset.js")
    assert missing.status == 404 and "immutable" not in missing.headers
    worker = client.request("/sw.js")
    assert worker.status == 200 and "no-store" in worker.headers
    assert "Service-Worker-Allowed: /" in worker.headers


def verify_reading(client, fixture):
    client.authenticate(fixture["reading_reader"])
    slug = fixture["reading_book"]["slug"]
    launched = client.request(f"/api/v1/reading/books/{slug}/launch/", {})
    assert launched.status == 200, "Protected reader launch failed."
    values = launched.json()
    path = values["resource_base"] + values["chapters"][0]["path"]
    chapter = client.request(path)
    assert chapter.status == 200 and "sandbox allow-same-origin" in chapter.headers
    assert "SAMEORIGIN" in chapter.headers and "no-store" in chapter.headers
    client.headers["Range"] = "bytes=0-15"
    partial = client.request(path)
    assert partial.status == 206 and partial.body == chapter.body[:16]
    del client.headers["Range"]
    downloaded = client.request(f"/api/v1/reading/books/{slug}/download/")
    assert downloaded.status == 200 and downloaded.body.startswith(b"PK")
    assert "X-Accel-Redirect:" not in downloaded.headers
    assert client.request("/api/v1/manage/jobs/").status == 403
    return path


def verify_worker(client, fixture):
    client.authenticate(fixture["administrator"])
    asset = fixture["pending_asset"]
    command = {
        "operation_id": asset["operation_id"],
        "expected_updated_at": asset["updated_at"],
    }
    path = f"/api/v1/manage/assets/{asset['id']}/prepare/"
    response = client.request(path, command)
    assert response.status == 202, "Preparation request failed."
    replayed = client.request(path, command)
    assert replayed.status == 202 and replayed.json() == response.json()
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        status = client.request(response.json()["status_url"])
        assert status.status == 200
        job = status.json()
        if job["state"] == "succeeded":
            assert job["attempt_count"] == 1 and job["checkpoint_saved"]
            assert job["stage"] == "prepared"
            return response.json()["operation_id"]
        assert job["state"] not in {"failed", "cancelled"}, (
            "Background preparation failed."
        )
        time.sleep(1)
    raise AssertionError("The live broker/worker preparation did not complete.")


def verify_catalog_creation(client, fixture):
    client.authenticate(fixture["administrator"])
    identifier = str(uuid4())
    command = {
        "operation_id": identifier,
        "title": f"কাগজের নথি {identifier[:8]}",
        "record_type": "manual",
        "edition": "দ্বিতীয় সংস্করণ",
        "manual_price": "250.00",
    }
    response = client.request("/api/v1/manage/books/", command)
    assert response.status == 201 and response.json()["state"] == "needs_review"
    replayed = client.request("/api/v1/manage/books/", command)
    assert replayed.status == 201 and replayed.json()["id"] == identifier
    assert client.request(f"/api/v1/manage/book-creations/{identifier}/").status == 200
    assert client.request("/manage/books/new/").status == 200
    client.authenticate(fixture["reading_reader"])
    assert client.request("/api/v1/manage/books/", command).status == 403


def main():
    directory = Path(os.environ["DEPLOYMENT_TEST_DIRECTORY"])
    fixture = json.loads((directory / "fixture.json").read_text())
    client = LocalHTTPSClient(directory)
    client.wait_until_ready()
    verify_public(client, fixture)
    resource = verify_reading(client, fixture)
    job_id = verify_worker(client, fixture)
    verify_catalog_creation(client, fixture)
    client.headers.clear()
    client.cookie = directory / "anonymous-cookies.txt"
    assert client.request(resource).status == 403
    print(
        f"Isolated HTTPS checks passed: SSR, SEO, protected bytes/ranges, permissions, and live preparation. job_id={job_id}"
    )


if __name__ == "__main__":
    main()
