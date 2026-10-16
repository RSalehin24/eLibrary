import hashlib
from dataclasses import dataclass

from django.conf import settings
from django.http import Http404

from apps.access.asset_names import asset_download_filename
from apps.access.storage import open_asset_stream
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

ASSET_READ_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class KindlePayload:
    filename: str
    content: bytes
    checksum: str


def checked_attachment_size(size):
    if size > settings.KINDLE_MAX_ATTACHMENT_BYTES:
        raise ExecutionFailure(FailureKind.PERMANENT, "attachment_too_large")


def read_attachment(stream):
    chunks = []
    size = 0
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(ASSET_READ_CHUNK_BYTES), b""):
        size += len(chunk)
        checked_attachment_size(size)
        digest.update(chunk)
        chunks.append(chunk)
    if not size:
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_empty")
    return b"".join(chunks), digest.hexdigest()


def load_kindle_payload(asset):
    checked_attachment_size(asset.file_size)
    try:
        stream = open_asset_stream(asset)
        try:
            content, checksum = read_attachment(stream)
        finally:
            stream.close()
    except Http404 as error:
        raise ExecutionFailure(FailureKind.PERMANENT, "asset_missing") from error
    except OSError as error:
        raise ExecutionFailure(FailureKind.TRANSIENT, "storage_unavailable") from error
    return KindlePayload(asset_download_filename(asset.book, asset), content, checksum)
