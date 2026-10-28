import hashlib
import logging
import zipfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

from apps.access.reading.epub_archive import checked_entries
from apps.access.reading.epub_manifest import publication_manifest
from apps.access.reading.epub_paths import InvalidEpub
from apps.access.reading.preparation import prepare_epub_asset
from apps.catalog.models import (
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
    MetadataVersion,
)
from apps.common.models import AuditLog, LifecycleState
from apps.processing.job_models import SOURCE_ACTIVE_STATES, BackgroundJobKind
from django.db import DatabaseError, transaction
from rest_framework.exceptions import APIException, ValidationError

from .epub_html import stage_epub_html
from .epub_source_proof import verify_uploaded_source_text
from .service import EditorialConflict, revision_checked_book

MAX_MANUAL_EPUB_BYTES = 24 * 1024 * 1024
logger = logging.getLogger(__name__)


class EpubStorageUnavailable(APIException):
    status_code = 503
    default_code = "storage_unavailable"
    default_detail = (
        "EPUB storage is temporarily unavailable. The current book is unchanged."
    )


@contextmanager
def uploaded_storage_guard():
    try:
        yield
    except (DatabaseError, OSError):
        logger.warning("EPUB storage or publication persistence is unavailable.")
        raise EpubStorageUnavailable() from None


def validate_epub_upload(upload):
    if (
        Path(upload.name).suffix.lower() != ".epub"
        or upload.size is None
        or upload.size > MAX_MANUAL_EPUB_BYTES
    ):
        raise ValidationError("Upload an EPUB no larger than 24 MiB.")
    try:
        with zipfile.ZipFile(upload) as archive:
            publication_manifest(archive, checked_entries(archive))
    except (
        InvalidEpub,
        KeyError,
        UnicodeError,
        ElementTree.ParseError,
        zipfile.BadZipFile,
    ):
        raise ValidationError("Upload a valid, readable EPUB archive.") from None
    finally:
        upload.seek(0)


def upload_checksum(upload):
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def stage_uploaded_asset(book, upload):
    asset = GeneratedAsset(book=book, asset_type=GeneratedAssetType.EPUB)
    asset.checksum = upload_checksum(upload)
    asset.file.save(f"{uuid4().hex}.epub", upload, save=False)
    asset.status = GeneratedAssetStatus.READY
    asset.content_type = "application/epub+zip"
    asset.file_size = upload.size
    asset.source_job = None
    asset.legacy_path = ""
    asset.storage_path = asset.file.name or ""
    return asset


def require_uploadable_book(book):
    unfinished = book.background_jobs.filter(
        kind=BackgroundJobKind.PROCESS_SOURCE, state__in=SOURCE_ACTIVE_STATES
    )
    if unfinished.exists():
        raise EditorialConflict("Finish the current source operation before uploading.")


@transaction.atomic
def uploadable_revision(actor, book_id, expected):
    book = revision_checked_book(actor, book_id, expected)
    require_uploadable_book(book)
    return book


def preserve_previous_asset(actor, book):
    previous = book.generated_assets.filter(asset_type=GeneratedAssetType.EPUB).first()
    if previous is None:
        return
    MetadataVersion.objects.create(
        book=book,
        created_by=actor,
        source="before_epub_upload",
        snapshot={
            "epub_asset": {
                "file": previous.file.name,
                "legacy_path": previous.legacy_path,
                "storage_path": previous.storage_path,
                "checksum": previous.checksum,
                "file_size": previous.file_size,
                "content_type": previous.content_type,
                "source_job_id": str(previous.source_job_id)
                if previous.source_job_id
                else None,
            }
        },
    )


@transaction.atomic
def commit_uploaded_asset(actor, command, staged):
    book_id, expected = command
    book = uploadable_revision(actor, book_id, expected)
    return activate_uploaded_assets(actor, book, staged)


def activate_uploaded_assets(actor, book, staged):
    asset, publication, html = staged
    verify_uploaded_source_text(book, publication)
    preserve_previous_asset(actor, book)
    for candidate in (asset, html):
        commit_staged_asset(book, candidate)
    if book.state != LifecycleState.ARCHIVED:
        book.state = LifecycleState.PUBLISHED
    book.save(update_fields=["state", "updated_at"])
    AuditLog.objects.create(
        actor=actor,
        verb="catalog.epub.upload",
        target_type=book._meta.label_lower,
        target_id=str(book.pk),
        payload={"checksum": asset.checksum, "file_size": asset.file_size},
    )
    return book


def commit_staged_asset(book, asset):
    GeneratedAsset.objects.update_or_create(
        book=book,
        asset_type=asset.asset_type,
        defaults={
            field: getattr(asset, field)
            for field in (
                "file",
                "checksum",
                "status",
                "content_type",
                "file_size",
                "source_job",
                "legacy_path",
                "storage_path",
                "is_protected",
            )
        },
    )


def replace_managed_epub(actor, book_id, values):
    with uploaded_storage_guard():
        book = uploadable_revision(actor, book_id, values["expected_updated_at"])
        staged = prepare_uploaded_assets(book, values["file"])
        return commit_uploaded_asset(
            actor, (book_id, values["expected_updated_at"]), staged
        )


def prepare_uploaded_assets(book, upload):
    try:
        asset = stage_uploaded_asset(book, upload)
        publication = prepare_epub_asset(asset)
        if publication.checksum != asset.checksum:
            raise InvalidEpub("The uploaded EPUB changed during preparation.")
        verify_uploaded_source_text(book, publication)
        html = stage_epub_html(book, publication)
        return asset, publication, html
    except InvalidEpub as error:
        raise ValidationError({"file": str(error)}, code="invalid_epub") from None
    except OSError:
        logger.warning("Manual EPUB storage or reader preparation is unavailable.")
        raise EpubStorageUnavailable() from None
