import json
import os
from urllib.parse import urljoin, urlsplit

import requests


def verified_base_url():
    value = os.environ["FOUNDATION_PROXY_URL"].rstrip("/")
    url = urlsplit(value)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "This verification requires an isolated loopback HTTP proxy."
        )
    return value


def reading_session(base, fixture):
    session = requests.Session()
    session.trust_env = False
    cookie = fixture["reading_reader"]["session"]
    session.cookies.set(cookie["name"], cookie["value"])
    response = session.get(base + "/api/v1/auth/session/", timeout=10)
    response.raise_for_status()
    session.headers["X-CSRFToken"] = response.json()["csrf_token"]
    slug = fixture["reading_book"]["slug"]
    response = session.post(base + f"/api/v1/reading/books/{slug}/launch/", timeout=10)
    response.raise_for_status()
    return session, response.json()


def verify_accelerated_resources(base, session, launched):
    chapter = launched["chapters"][0]["path"]
    path = launched["resource_base"] + chapter
    response = session.get(urljoin(base, path), timeout=10)
    response.raise_for_status()
    assert response.content and "X-Accel-Redirect" not in response.headers
    assert response.headers["Content-Type"].split(";")[0] == "application/xhtml+xml"
    assert "private" in response.headers["Cache-Control"]
    assert "sandbox allow-same-origin" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-Robots-Tag"] == "noindex"
    partial = session.get(
        urljoin(base, path), headers={"Range": "bytes=0-15"}, timeout=10
    )
    assert partial.status_code == 206 and len(partial.content) == 16
    assert partial.content == response.content[:16]
    anonymous = requests.Session()
    anonymous.trust_env = False
    assert anonymous.get(urljoin(base, path), timeout=10).status_code == 403
    return chapter


def verify_private_routes(base, session, fixture):
    for path in (
        "/_protected/",
        "/media/protected/",
        "/api/catalog/books/",
        "/api/auth/demo-login/",
    ):
        assert session.get(base + path, timeout=10).status_code == 404
    slug = fixture["reading_book"]["slug"]
    response = session.get(base + f"/api/v1/reading/books/{slug}/download/", timeout=10)
    response.raise_for_status()
    assert (
        response.content.startswith(b"PK")
        and "attachment;" in response.headers["Content-Disposition"]
    )
    assert "X-Accel-Redirect" not in response.headers


def main():
    base = verified_base_url()
    with open(os.environ["FOUNDATION_FIXTURE_PATH"]) as stream:
        fixture = json.load(stream)
    session, launched = reading_session(base, fixture)
    try:
        verify_accelerated_resources(base, session, launched)
        verify_private_routes(base, session, fixture)
    finally:
        session.close()
    print(
        "Protected proxy checks passed: authorized bytes, byte ranges, sandbox, downloads, and route isolation."
    )


if __name__ == "__main__":
    main()
