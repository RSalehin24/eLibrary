from pathlib import Path

from django.http import Http404

from apps.access.storage import asset_is_available, open_asset_stream
from apps.ingestion.services.submissions_support.persistence import (
    export_payload_from_book,
)

from .covers import validated_cover
from .policy import MAX_RESPONSE_BYTES


def regenerated_export_payload(book, payload):
    metadata = export_payload_from_book(book, payload)
    for field in ("book_title", "author", "series", "book_type"):
        payload[field] = metadata[field]
    if "cover" in book.metadata_overrides:
        payload["cover"] = ""
        if book.metadata_overrides["cover"] is None:
            return payload
    elif payload.get("cover"):
        return payload
    cover = book.generated_assets.filter(asset_type="cover", status="ready").first()
    if cover is None or not asset_is_available(cover):
        return payload
    suffix = Path(cover.file.name or cover.legacy_path).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        return payload
    target = Path(payload["output_folder"]) / f"previous-cover{suffix}"
    try:
        with open_asset_stream(cover) as source:
            data = source.read(MAX_RESPONSE_BYTES + 1)
    except Http404:
        return payload
    if len(data) <= MAX_RESPONSE_BYTES:
        target.write_bytes(data)
        payload["cover"] = validated_cover(target.parent, target.name)
    return payload
