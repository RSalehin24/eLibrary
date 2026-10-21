import re

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse

from .protected_files import protected_file_response

MEDIA_CHUNK_BYTES = 64 * 1024


def requested_byte_range(value, size):
    if not value.startswith("bytes=") or "," in value:
        return None
    matched = (
        re.fullmatch(r"bytes=([0-9]*)-([0-9]*)", value) if len(value) <= 200 else None
    )
    if not matched or not any(matched.groups()) or not size:
        raise ValueError("Unsatisfiable media range.")
    first, last = matched.groups()
    start = int(first) if first else max(0, size - int(last))
    end = min(int(last), size - 1) if first and last else size - 1
    if start >= size or end < start or not first and int(last) == 0:
        raise ValueError("Unsatisfiable media range.")
    return start, end


class MediaRangeStream:
    def __init__(self, path, bounds):
        self.stream = path.open("rb")
        self.stream.seek(bounds[0])
        self.remaining = bounds[1] - bounds[0] + 1

    def __iter__(self):
        return self

    def __next__(self):
        if not self.remaining:
            self.close()
            raise StopIteration
        content = self.stream.read(min(self.remaining, MEDIA_CHUNK_BYTES))
        self.remaining -= len(content)
        if not content:
            self.close()
            raise StopIteration
        return content

    def close(self):
        self.stream.close()


def partial_media_response(path, bounds, content_type):
    size = path.stat().st_size
    response = StreamingHttpResponse(
        MediaRangeStream(path, bounds), status=206, content_type=content_type
    )
    response["Content-Range"] = f"bytes {bounds[0]}-{bounds[1]}/{size}"
    response["Content-Length"] = bounds[1] - bounds[0] + 1
    return response


def protected_media_response(path, request, content_type):
    if settings.PROTECTED_FILES_USE_NGINX:
        return protected_file_response(path, content_type)
    size = path.stat().st_size
    value = "" if request.headers.get("If-Range") else request.headers.get("Range", "")
    try:
        bounds = requested_byte_range(value, size)
    except ValueError:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{size}"
    else:
        response = (
            partial_media_response(path, bounds, content_type)
            if bounds
            else protected_file_response(path, content_type)
        )
    response["Accept-Ranges"] = "bytes"
    return response
