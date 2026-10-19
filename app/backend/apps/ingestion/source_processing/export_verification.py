from collections import Counter
from zipfile import BadZipFile, ZipFile

from apps.access.reading.epub_archive import (
    MAX_ARCHIVE_BYTES,
    MAX_EXPANDED_BYTES,
    checked_entries,
    read_entry,
)
from apps.access.reading.epub_paths import InvalidEpub
from apps.catalog.models import GeneratedAssetType
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .content_text import canonical_text


def epub_export_text(path):
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise InvalidEpub("EPUB archive exceeds the size limit.")
    with ZipFile(path) as archive:
        entries = checked_entries(archive)
        return " ".join(
            canonical_text(read_entry(archive, entry).decode("utf-8-sig"))
            for name, entry in entries.items()
            if name.lower().endswith((".xhtml", ".html", ".htm"))
        )


def verify_reading_text(result, actual):
    expected = Counter(
        text
        for section in result["document"].get("sections", [])
        if section.get("section_type") == "body"
        and (text := canonical_text(section.get("html", "")))
    )
    return bool(expected) and all(
        actual.count(body) >= count for body, count in expected.items()
    )


def verify_export_text(result, paths):
    html_path = paths[GeneratedAssetType.HTML]
    if html_path.stat().st_size > MAX_EXPANDED_BYTES:
        raise InvalidEpub("HTML export exceeds the size limit.")
    actual = (
        canonical_text(html_path.read_text(encoding="utf-8-sig")),
        epub_export_text(paths[GeneratedAssetType.EPUB]),
    )
    return all(verify_reading_text(result, text) for text in actual)


def require_verified_exports(result, paths):
    try:
        verified = verify_export_text(result, paths)
    except (BadZipFile, InvalidEpub, UnicodeError):
        verified = False
    if not verified:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_export_content_mismatch")
