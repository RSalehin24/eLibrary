import pytest
from apps.access.protected_media import MediaRangeStream, protected_media_response
from django.test import RequestFactory


@pytest.mark.parametrize(
    "case",
    [
        ("bytes=2-4", b"234", "2-4"),
        ("bytes=7-", b"789", "7-9"),
        ("bytes=-3", b"789", "7-9"),
        ("bytes=7-99", b"789", "7-9"),
        ("bytes=-99", b"0123456789", "0-9"),
    ],
)
def test_media_supports_bounded_open_and_suffix_byte_ranges(tmp_path, settings, case):
    header, expected, bounds = case
    settings.PROTECTED_FILES_USE_NGINX = False
    path = tmp_path / "voice.wav"
    path.write_bytes(b"0123456789")
    response = protected_media_response(
        path, RequestFactory().get("/audio", HTTP_RANGE=header), "audio/wav"
    )
    try:
        assert response.status_code == 206
        assert response["Content-Range"] == f"bytes {bounds}/10"
        assert int(response["Content-Length"]) == len(expected)
        assert response["Accept-Ranges"] == "bytes"
        assert b"".join(response.streaming_content) == expected
    finally:
        response.close()


@pytest.mark.parametrize(
    "header",
    [
        "bytes=10-",
        "bytes=9-2",
        "bytes=-0",
        "bytes=-",
        "bytes=NaN-2",
        "bytes=" + "9" * 300 + "-",
    ],
)
def test_invalid_or_unsatisfiable_ranges_expose_no_file_bytes(
    tmp_path, settings, header
):
    settings.PROTECTED_FILES_USE_NGINX = False
    path = tmp_path / "voice.wav"
    path.write_bytes(b"0123456789")
    response = protected_media_response(
        path, RequestFactory().get("/audio", HTTP_RANGE=header), "audio/wav"
    )
    assert response.status_code == 416 and response["Content-Range"] == "bytes */10"
    assert response.content == b""


def test_if_range_and_unsupported_range_units_return_the_whole_private_representation(
    tmp_path, settings
):
    settings.PROTECTED_FILES_USE_NGINX = False
    path = tmp_path / "voice.wav"
    path.write_bytes(b"0123456789")
    for headers in [
        {"HTTP_RANGE": "items=1-2"},
        {"HTTP_RANGE": "bytes=0-1,4-5"},
        {"HTTP_RANGE": "bytes=2-3", "HTTP_IF_RANGE": '"old-edition"'},
    ]:
        response = protected_media_response(
            path, RequestFactory().get("/audio", **headers), "audio/wav"
        )
        try:
            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"0123456789"
        finally:
            response.close()


def test_range_stream_releases_its_file_even_when_a_download_is_cancelled(tmp_path):
    path = tmp_path / "voice.wav"
    path.write_bytes(b"0123456789")
    stream = MediaRangeStream(path, (2, 8))
    stream.close()
    assert stream.stream.closed
