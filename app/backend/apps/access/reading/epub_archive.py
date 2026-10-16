import stat
import zipfile

from .epub_paths import InvalidEpub, resource_path

MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_RESOURCE_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_RESOURCES = 10_000
MAX_COMPRESSION_RATIO = 100
MAX_XML_BYTES = 2 * 1024 * 1024


def checked_entries(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    entries: dict[str, zipfile.ZipInfo] = {}
    if len(archive.infolist()) > MAX_RESOURCES:
        raise InvalidEpub("EPUB contains too many resources.")
    for entry in archive.infolist():
        path = resource_path(entry.filename.rstrip("/"))
        validate_entry(entry)
        if path in entries:
            raise InvalidEpub("EPUB contains duplicate resource paths.")
        entries[path] = entry
    if sum(entry.file_size for entry in entries.values()) > MAX_EXPANDED_BYTES:
        raise InvalidEpub("EPUB expanded size exceeds the limit.")
    return entries


def validate_entry(entry: zipfile.ZipInfo) -> None:
    kind = stat.S_IFMT(entry.external_attr >> 16)
    if entry.flag_bits & 1 or kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise InvalidEpub("Encrypted or special EPUB resources are unsupported.")
    if entry.file_size > MAX_RESOURCE_BYTES:
        raise InvalidEpub("EPUB resource exceeds the size limit.")
    if entry.file_size > max(entry.compress_size, 1) * MAX_COMPRESSION_RATIO:
        raise InvalidEpub("EPUB compression ratio exceeds the limit.")


def read_entry(archive: zipfile.ZipFile, entry: zipfile.ZipInfo) -> bytes:
    with archive.open(entry) as stream:
        data = stream.read(MAX_RESOURCE_BYTES + 1)
    if len(data) > MAX_RESOURCE_BYTES:
        raise InvalidEpub("EPUB resource exceeds the size limit.")
    return data
