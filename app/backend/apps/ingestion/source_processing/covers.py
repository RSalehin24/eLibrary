import logging
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, UnidentifiedImageError

from apps.ingestion.pipeline.book_manifest import download_cover_asset
from apps.processing.jobs.execution_errors import ExecutionFailure

from .policy import require_source_url, source_hosts
from .transport import ControlledSourceSession

OPTIONAL_COVER_FAILURES = {
    "source_url_not_allowed",
    "source_connection_unavailable",
    "source_response_too_large",
}
logger = logging.getLogger(__name__)


def validated_cover(folder, name):
    if not name:
        return ""
    try:
        with Image.open(Path(folder) / name) as image:
            if (
                image.format not in {"JPEG", "PNG", "WEBP"}
                or image.width * image.height > 20000000
            ):
                return ""
            image.verify()
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        logger.warning("The source cover is not a valid raster image.")
        return ""
    return name


def download_source_cover(url, folder, session):
    if not url:
        return ""
    try:
        hosts = source_hosts()
        media_hosts = hosts | {f"cdn.{host.removeprefix('www.')}" for host in hosts}
        require_source_url(url, media_hosts)
        if urlsplit(url).hostname in hosts:
            return validated_cover(folder, download_cover_asset(url, folder, session))
        with ControlledSourceSession(
            session.before_request, session.wait_for_slot
        ) as media:
            media.allowed_hosts = frozenset({urlsplit(url).hostname or ""})
            # Public CDN media must never receive authenticated source cookies.
            media.cookies.clear()
            return validated_cover(folder, download_cover_asset(url, folder, media))
    except ExecutionFailure as error:
        if error.failure.code in OPTIONAL_COVER_FAILURES:
            # Covers can be generated locally; optional media must not block the book.
            return ""
        raise
