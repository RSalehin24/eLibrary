import hashlib
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction

from apps.access.publication_models import PreparationState, PreparedPublication
from apps.access.storage import open_asset_stream
from apps.catalog.models import GeneratedAsset, GeneratedAssetType

from .document_safety import PREPARATION_VERSION, safe_document
from .epub_archive import MAX_ARCHIVE_BYTES, checked_entries, read_entry
from .epub_manifest import DOCUMENT_TYPES, publication_manifest
from .epub_paths import InvalidEpub, resource_path


def publication_directory(publication) -> Path:
    key = publication.storage_reference
    if len(key) != 64 or any(character not in "0123456789abcdef" for character in key):
        raise InvalidEpub("Invalid prepared publication reference.")
    return Path(settings.MEDIA_ROOT) / "protected" / "reader" / key


@contextmanager
def asset_snapshot(asset):
    with tempfile.TemporaryFile() as snapshot:
        stream = open_asset_stream(asset)
        try:
            checksum, size = copy_snapshot(stream, snapshot)
        finally:
            stream.close()
        snapshot.seek(0)
        yield snapshot, checksum, size


def copy_snapshot(source, destination):
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: source.read(64 * 1024), b""):
        size += len(chunk)
        if size > MAX_ARCHIVE_BYTES:
            raise InvalidEpub("EPUB archive exceeds the size limit.")
        digest.update(chunk)
        destination.write(chunk)
    return digest.hexdigest(), size


def extract_publication(snapshot, destination):
    try:
        with zipfile.ZipFile(snapshot) as archive:
            entries = checked_entries(archive)
            manifest = publication_manifest(archive, entries)
            extract_resources(archive, entries, (manifest, destination))
            manifest["preparation_version"] = PREPARATION_VERSION
        return manifest
    except (KeyError, UnicodeError, ElementTree.ParseError, zipfile.BadZipFile) as exc:
        raise InvalidEpub("EPUB metadata or resources are invalid.") from exc


def extract_resources(archive, entries, publication):
    manifest, destination = publication
    chapters = {chapter["path"]: chapter for chapter in manifest["chapters"]}
    for resource in manifest["resources"]:
        path = resource_path(resource["path"])
        data = read_entry(archive, entries[path])
        if resource["media_type"] in DOCUMENT_TYPES:
            data = safe_document(data)
        resource["size"] = len(data)
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if path in chapters:
            chapters[path]["label"] = chapter_label(data, chapters[path]["label"])


def chapter_label(data, fallback):
    document = BeautifulSoup(data, "html.parser")
    title = document.find(["h1", "h2", "title"])
    label = title.get_text(" ", strip=True) if title else ""
    return label[:255] or fallback


def prepare_epub_asset(asset):
    if asset.asset_type != GeneratedAssetType.EPUB:
        raise InvalidEpub("Only EPUB assets can be prepared for reading.")
    revision = asset.updated_at
    with asset_snapshot(asset) as (snapshot, checksum, size):
        publication, _ = PreparedPublication.objects.get_or_create(checksum=checksum)
        publication = prepare_locked_publication(publication.pk, snapshot, size)
    if publication.state != PreparationState.READY:
        raise InvalidEpub(publication.error)
    GeneratedAsset.objects.filter(pk=asset.pk, updated_at=revision).update(
        checksum=checksum
    )
    return publication


@transaction.atomic
def prepare_locked_publication(identifier, snapshot, size):
    publication = PreparedPublication.objects.select_for_update().get(pk=identifier)
    if publication.state == PreparationState.READY and publication_files_available(
        publication
    ):
        return publication
    publication.state = PreparationState.PREPARING
    try:
        write_publication(publication, snapshot)
    except InvalidEpub as exc:
        publication.state = PreparationState.FAILED
        publication.error = str(exc)
    publication.file_size = size
    publication.save()
    return publication


def write_publication(publication, snapshot):
    publication.storage_reference = publication.checksum
    destination = publication_directory(publication)
    if destination.exists():
        publication.storage_reference = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        destination = publication_directory(publication)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staged = Path(temporary) / "publication"
        staged.mkdir()
        manifest = extract_publication(snapshot, staged)
        staged.rename(destination)
    publication.manifest = manifest
    publication.state = PreparationState.READY
    publication.error = ""


def publication_files_available(publication):
    if publication.manifest.get("preparation_version") != PREPARATION_VERSION:
        return False
    directory = publication_directory(publication)
    return all(
        (directory / resource["path"]).is_file()
        and (directory / resource["path"]).stat().st_size == resource["size"]
        for resource in publication.manifest.get("resources", [])
    ) and bool(publication.manifest.get("chapters"))
