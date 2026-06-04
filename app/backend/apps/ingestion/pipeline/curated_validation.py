import re

from bs4 import BeautifulSoup

from apps.catalog.models import CuratedDocumentStatus, CuratedSectionType
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.services.normalization import plain_text_from_html


SOURCE_CHROME_PATTERNS = (
    "leave a reply",
    "logged in",
    "login",
    "my account",
    "related books",
    "প্রাসঙ্গিক বই",
    "মন্তব্য করুন",
    "লগইন",
)
SOURCE_CHROME_CONTAINS_PATTERNS = {"logged in", "login", "লগইন"}
SOURCE_CHROME_MAX_BLOCK_LENGTH = 160
SOURCE_CHROME_BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote")


def path_tuple(value):
    if isinstance(value, (list, tuple)):
        return tuple(clean_display_text(part) for part in value if clean_display_text(part))
    return ()


def iter_toc_entries(entries, parent_path=()):
    for entry in entries or []:
        current_path = path_tuple(entry.get("path")) or (*parent_path, clean_display_text(entry.get("title", "")))
        yield entry, current_path
        yield from iter_toc_entries(entry.get("children", []), current_path)


def generated_toc_from_content_items(content_items):
    return [
        {
            "title": item.get("title", ""),
            "type": item.get("type", "lesson"),
            "has_content": None if item.get("has_content") is None else bool(plain_text_from_html(item.get("content", ""))),
            "path": list(path_tuple(item.get("path")) or (item.get("title", ""),)),
        }
        for item in content_items or []
        if clean_display_text(item.get("title", ""))
    ]


def duplicate_paths(content_items):
    seen = set()
    duplicates = []
    for item in content_items or []:
        path = path_tuple(item.get("path")) or (clean_display_text(item.get("title", "")),)
        if not path:
            continue
        if path in seen:
            duplicates.append(" / ".join(path))
        seen.add(path)
    return duplicates


def dead_toc_leaves(toc, content_items):
    content_paths = {
        path_tuple(item.get("path")) or (clean_display_text(item.get("title", "")),)
        for item in content_items or []
        if plain_text_from_html(item.get("content", "")) or item.get("has_content") is None
    }
    dead = []
    for entry, path in iter_toc_entries(toc):
        if entry.get("children"):
            continue
        if path and path not in content_paths and entry.get("has_content", True):
            dead.append(" / ".join(path))
    return dead


def empty_content_toc_leaves(toc):
    empty = []
    for entry, path in iter_toc_entries(toc):
        if entry.get("children"):
            continue
        if entry.get("type") == "section":
            continue
        if path and entry.get("has_content") is False:
            empty.append(" / ".join(path))
    return empty


def is_source_chrome_block(normalized, normalized_pattern, pattern):
    if not normalized or not normalized_pattern:
        return False
    if normalized == normalized_pattern:
        return True
    if len(normalized) > SOURCE_CHROME_MAX_BLOCK_LENGTH:
        return False

    bounded_pattern = rf"(^|\s){re.escape(normalized_pattern)}($|\s)"
    if pattern in SOURCE_CHROME_CONTAINS_PATTERNS:
        return bool(re.search(bounded_pattern, normalized))
    return normalized.startswith(f"{normalized_pattern} ")


def source_chrome_hits(sections):
    hits = []
    for section in sections or []:
        if section.get("section_type") != CuratedSectionType.BODY:
            continue

        soup = BeautifulSoup(section.get("html", ""), "html.parser")
        block_texts = [
            clean_display_text(block.get_text(" ", strip=True))
            for block in soup.find_all(SOURCE_CHROME_BLOCK_TAGS)
        ] or [plain_text_from_html(section.get("html", ""))]
        for pattern in SOURCE_CHROME_PATTERNS:
            normalized_pattern = normalize_catalog_text(pattern)
            if not normalized_pattern:
                continue
            for block_text in block_texts:
                normalized = normalize_catalog_text(block_text)
                if is_source_chrome_block(normalized, normalized_pattern, pattern):
                    hits.append({"section_id": section.get("section_id", ""), "pattern": pattern})
                    break
    return hits


def fetched_content_assignment_warnings(snapshot, sections):
    raw = snapshot.get("raw_scrape_payload") or {}
    warnings = []
    has_raw_main = bool(plain_text_from_html(raw.get("main_content", "")))
    has_section_main = any(section.get("source_location") == "raw_scrape_payload.main_content" for section in sections)
    if has_raw_main and not has_section_main:
        warnings.append("Main content was fetched but not assigned to a curated section.")
    return warnings


def source_page_fetch_errors(snapshot):
    errors = []
    for page in snapshot.get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        url = page.get("url", "")
        status = page.get("status", "")
        status_code = page.get("status_code")
        if status != "fetched":
            detail = f"Source page was not fetched: {url}."
            if status_code:
                detail = f"Source page was not fetched: {url} ({status_code})."
            errors.append(detail)
            continue
        try:
            parsed_status_code = int(status_code or 0)
        except (TypeError, ValueError):
            parsed_status_code = 0
        if parsed_status_code and parsed_status_code != 200:
            errors.append(f"Source page returned non-200 status: {url} ({status_code}).")
    return errors


def validate_document(document, snapshot):
    projection = document.get("projection") or {}
    sections = document.get("sections") or []
    toc = projection.get("toc") or []
    content_items = projection.get("content_items") or []
    errors = []
    warnings = []

    clean_title = clean_display_text(document.get("book", {}).get("clean_title", ""))
    normalized_title = normalize_catalog_text(clean_title)
    if not clean_title:
        errors.append("Missing required title.")
    elif normalized_title in {"book title", "page not found"}:
        errors.append(f"Non-book fallback title extracted: {clean_title}.")
    if not clean_display_text(document.get("canonical_url", "")):
        errors.append("Missing canonical URL.")

    body_sections = [
        section
        for section in sections
        if section.get("section_type") == CuratedSectionType.BODY
        and plain_text_from_html(section.get("html", ""))
    ]
    if not body_sections:
        errors.append("Missing body content.")

    if content_items and not toc:
        errors.append("Structured content is missing a generated TOC.")
    for index, item in enumerate(content_items):
        if not isinstance(item, dict):
            errors.append(f"Content item {index + 1} is not structured.")
            continue
        path = path_tuple(item.get("path")) or (clean_display_text(item.get("title", "")),)
        label = " / ".join(path) if path else str(index + 1)
        if not path:
            errors.append(f"Content item {index + 1} is missing a title/path.")
        if not plain_text_from_html(item.get("content", "")) and item.get("has_content") is not None:
            errors.append(f"Content item has no body: {label}.")
    for duplicate_path in duplicate_paths(content_items):
        errors.append(f"Duplicate content path: {duplicate_path}.")
    for empty_path in empty_content_toc_leaves(toc):
        errors.append(f"TOC content leaf has no extracted body: {empty_path}.")
    for dead_path in dead_toc_leaves(toc, content_items):
        errors.append(f"Dead TOC leaf without content: {dead_path}.")
    for hit in source_chrome_hits(sections):
        errors.append(f"Source chrome found in body section {hit['section_id']}: {hit['pattern']}.")
    errors.extend(source_page_fetch_errors(snapshot))

    warnings.extend(fetched_content_assignment_warnings(snapshot, sections))
    low_confidence = [
        section.get("section_id", "")
        for section in sections
        if section.get("confidence", 1) < 0.75
    ]
    if low_confidence:
        warnings.append(f"Low-confidence sections: {', '.join(low_confidence)}.")

    hard_missing = any(error in {"Missing required title.", "Missing canonical URL.", "Missing body content."} for error in errors)
    status = CuratedDocumentStatus.VALIDATED
    if errors:
        status = CuratedDocumentStatus.INVALID if hard_missing else CuratedDocumentStatus.REVIEW_REQUIRED

    return {
        "is_valid": not errors,
        "status": getattr(status, "value", status),
        "errors": errors,
        "warnings": warnings,
        "body_section_count": len(body_sections),
        "entity_count": len(document.get("entities") or []),
        "section_count": len(sections),
    }
