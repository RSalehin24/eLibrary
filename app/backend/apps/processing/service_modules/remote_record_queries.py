"""Remote record queries."""

from urllib.parse import unquote, urlparse

from django.utils import timezone

from ..models import (
    BookCreationState,
)
from . import catalog_phase_helpers as _phase_helpers


def normalize_remote_record(payload):
    timestamp = (
        payload.get("updatedAt")
        or payload.get("updated_at")
        or timezone.now().isoformat()
    )
    category = str(payload.get("category") or "Uncategorized")
    was_incomplete = payload.get("wasIncomplete")
    if was_incomplete is None:
        was_incomplete = payload.get("was_incomplete")
    if was_incomplete is None:
        was_incomplete = _phase_helpers.category_is_incomplete(category)
    return {
        "id": str(payload.get("id") or payload.get("url") or ""),
        "name": str(payload.get("name") or payload.get("title") or "Untitled book"),
        "url": str(payload.get("url") or ""),
        "category": category,
        "writer": str(payload.get("writer") or payload.get("author") or ""),
        "translator": str(payload.get("translator") or ""),
        "composer": str(payload.get("composer") or ""),
        "publisher": str(payload.get("publisher") or ""),
        "updatedAt": timestamp,
        "bookCreationState": str(
            payload.get("bookCreationState")
            or payload.get("book_creation_state")
            or BookCreationState.NOT_CREATED
        ),
        "wasIncomplete": bool(was_incomplete),
        "resolvedFromIncomplete": bool(
            payload.get("resolvedFromIncomplete")
            or payload.get("resolved_from_incomplete")
        ),
        "willResolveToCategory": str(
            payload.get("willResolveToCategory")
            or payload.get("will_resolve_to_category")
            or ""
        ),
    }


def is_catalog_remote_page(page):
    return isinstance(page, list) and all(isinstance(item, dict) for item in page)


def catalog_remote_pages(remote_pages):
    if isinstance(remote_pages, list) and all(
        is_catalog_remote_page(page) for page in remote_pages
    ):
        return remote_pages
    return []


def source_catalog_entry_payload(entry):
    raw_data = entry.raw_data or {}
    category = (
        raw_data.get("category")
        or raw_data.get("resolvedCategory")
        or raw_data.get("resolved_category")
        or "Uncategorized"
    )
    parsed = urlparse((entry.source_url or "").strip())
    return {
        "id": str(entry.id),
        "name": entry.title,
        "url": entry.source_url,
        "displayUrl": unquote(entry.source_url or ""),
        "displayPath": unquote(parsed.path).strip("/") or parsed.netloc,
        "category": category,
        "writer": entry.author_line,
        "translator": raw_data.get("translator") or "",
        "composer": raw_data.get("composer") or "",
        "publisher": raw_data.get("publisher") or "",
        "updatedAt": entry.updated_at.isoformat(),
        "wasIncomplete": _phase_helpers.category_is_incomplete(category),
        "willResolveToCategory": raw_data.get("willResolveToCategory")
        or raw_data.get("will_resolve_to_category")
        or raw_data.get("resolvedCategory")
        or raw_data.get("resolved_category")
        or "",
    }
