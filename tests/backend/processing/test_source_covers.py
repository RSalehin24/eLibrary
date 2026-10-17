from io import BytesIO

import pytest
from apps.ingestion.source_processing.covers import (
    download_source_cover,
    validated_cover,
)
from apps.ingestion.source_processing.transport import ControlledSourceSession
from PIL import Image
from source_transport_fixture import FixtureAdapter, fixture_request_slot

pytestmark = pytest.mark.django_db


def test_oversized_cover_warning_is_rejected_with_warnings_as_errors(
    tmp_path, monkeypatch
):
    data = tmp_path / "oversized.png"
    Image.new("RGB", (30, 45), "red").save(data)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    assert validated_cover(tmp_path, data.name) == ""


def test_cdn_cover_download_is_bounded_and_does_not_send_source_cookies(
    settings, tmp_path, monkeypatch
):
    settings.SOURCE_SITE_HOST = "www.source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    data = BytesIO()
    Image.new("RGB", (30, 45), "red").save(data, format="JPEG")
    adapter = FixtureAdapter([(200, {"Content-Type": "image/jpeg"}, data.getvalue())])
    original = ControlledSourceSession(lambda: None, fixture_request_slot)
    original.cookies.set(
        "source_session", "private", domain=".source.test", secure=True
    )

    def media_session(boundary, pacing):
        session = ControlledSourceSession(boundary, pacing)
        session.cookies.set(
            "source_session", "private", domain=".source.test", secure=True
        )
        session.mount("https://", adapter)
        return session

    monkeypatch.setattr(
        "apps.ingestion.source_processing.covers.ControlledSourceSession", media_session
    )
    name = download_source_cover(
        "https://cdn.source.test/cover.jpg", tmp_path, original
    )
    assert (
        name == "book_cover.jpg" and (tmp_path / name).read_bytes() == data.getvalue()
    )
    assert "Cookie" not in adapter.calls[0][0].headers
    assert original.allowed_hosts == frozenset({"source.test", "www.source.test"})
    assert original.cookies.get("source_session") == "private"
    assert adapter.calls[0][1]["verify"] is True


@pytest.mark.parametrize(
    "host", ["images.source.test", "cdn.source.test.evil.test", "unrelated.test"]
)
def test_unrelated_image_hosts_do_not_change_book_source_policy(
    settings, tmp_path, host
):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    with ControlledSourceSession(lambda: None, fixture_request_slot) as session:
        assert (
            download_source_cover(f"https://{host}/cover.jpg", tmp_path, session) == ""
        )


def test_invalid_image_data_is_not_published(settings, tmp_path):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    adapter = FixtureAdapter(
        [(200, {"Content-Type": "image/jpeg"}, b"<script>not an image</script>")]
    )
    with ControlledSourceSession(lambda: None, fixture_request_slot) as session:
        session.mount("https://", adapter)
        assert (
            download_source_cover("https://source.test/cover.jpg", tmp_path, session)
            == ""
        )
