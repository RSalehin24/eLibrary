import hashlib
import logging
from uuid import uuid4

from apps.catalog.editorial.epub_uploads import commit_staged_asset
from apps.catalog.editorial.service import (
    record_metadata_version,
    revision_checked_book,
)
from apps.catalog.models import GeneratedAsset
from apps.common.models import AuditLog
from django.db import DatabaseError, transaction
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


class CoverStorageUnavailable(APIException):
    status_code = 503
    default_code = "storage_unavailable"
    default_detail = "Cover storage is unavailable. The current cover is unchanged."


def stage_cover(book, image):
    asset = GeneratedAsset(
        book=book, asset_type="cover", status="ready", content_type="image/png"
    )
    asset.checksum = hashlib.sha256(image.read()).hexdigest()
    image.seek(0)
    asset.file.save(f"{uuid4().hex}.png", image, save=False)
    asset.storage_path, asset.file_size = asset.file.name or "", image.size
    return asset


@transaction.atomic
def commit_cover(actor, command, staged):
    book = revision_checked_book(actor, command[0], command[1])
    record_metadata_version(book, actor)
    if staged is None:
        book.generated_assets.filter(asset_type="cover").delete()
    else:
        commit_staged_asset(book, staged)
    book.metadata_overrides = {
        **book.metadata_overrides,
        "cover": staged.checksum if staged else None,
    }
    book.save(update_fields=["metadata_overrides", "updated_at"])
    AuditLog.objects.create(
        actor=actor,
        verb="catalog.cover.update",
        target_type=book._meta.label_lower,
        target_id=str(book.pk),
        payload={"checksum": staged.checksum if staged else None},
    )
    return book


def replace_book_cover(actor, book_id, values):
    expected = values["expected_updated_at"]
    with transaction.atomic():
        book = revision_checked_book(actor, book_id, expected)
    try:
        staged = stage_cover(book, values["image"]) if values.get("image") else None
        return commit_cover(actor, (book_id, expected), staged)
    except (DatabaseError, OSError):
        logger.warning("Book cover storage or persistence is unavailable.")
        raise CoverStorageUnavailable() from None
