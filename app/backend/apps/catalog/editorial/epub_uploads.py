import hashlib
import zipfile
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

from apps.access.reading.epub_archive import checked_entries
from apps.access.reading.epub_manifest import publication_manifest
from apps.access.reading.epub_paths import InvalidEpub
from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType
from apps.common.models import AuditLog, LifecycleState, ReviewState
from apps.processing.job_models import SOURCE_ACTIVE_STATES, BackgroundJobKind
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .service import EditorialConflict, revision_checked_book

MAX_MANUAL_EPUB_BYTES = 24 * 1024 * 1024


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


def save_uploaded_asset(book, upload):
    asset, _ = GeneratedAsset.objects.get_or_create(
        book=book, asset_type=GeneratedAssetType.EPUB
    )
    asset.checksum = upload_checksum(upload)
    asset.file.save(f"{uuid4().hex}.epub", upload, save=False)
    asset.status = GeneratedAssetStatus.READY
    asset.content_type = "application/epub+zip"
    asset.file_size = upload.size
    asset.source_job = None
    asset.legacy_path = ""
    asset.storage_path = asset.file.name or ""
    asset.save()
    return asset


def require_uploadable_book(book):
    if book.record_type != "digital":
        raise ValidationError({"file": "EPUB uploads require a digital book record."})
    unfinished = book.background_jobs.filter(
        kind=BackgroundJobKind.PROCESS_SOURCE, state__in=SOURCE_ACTIVE_STATES
    )
    if unfinished.exists():
        raise EditorialConflict("Finish the current source operation before uploading.")


@transaction.atomic
def replace_managed_epub(actor, book_id, values):
    book = revision_checked_book(actor, book_id, values["expected_updated_at"])
    require_uploadable_book(book)
    asset = save_uploaded_asset(book, values["file"])
    book.editorial_reviewed_at = None
    book.review_state = ReviewState.PENDING
    book.state = LifecycleState.NEEDS_REVIEW
    book.save(
        update_fields=["editorial_reviewed_at", "review_state", "state", "updated_at"]
    )
    AuditLog.objects.create(
        actor=actor,
        verb="catalog.epub.upload",
        target_type=book._meta.label_lower,
        target_id=str(book.pk),
        payload={"checksum": asset.checksum, "file_size": asset.file_size},
    )
    return book
