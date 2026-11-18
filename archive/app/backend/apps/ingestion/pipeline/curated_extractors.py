import hashlib

from bs4 import BeautifulSoup

from apps.catalog.models import (
    ContributorRole,
    CuratedEntityType,
    CuratedSectionType,
)
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.services.normalization import (
    extract_front_matter_entries,
    normalize_scraped_book,
    plain_text_from_html,
)


PUBLICATION_KEYS = {
    "edition",
    "first_published",
    "language",
    "original_title",
    "page_count",
}
SOURCE_LOCATION_ROOT = "raw_scrape_payload"


def stable_section_id(prefix, value, index):
    seed = normalize_catalog_text(value) or str(index)
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{index:04d}-{digest}"


def evidence(value, entity_type, role, source_url, location, text, confidence, extractor, payload=None):
    return {
        "value": clean_display_text(value),
        "entity_type": entity_type,
        "role": role or "",
        "source_url": source_url,
        "source_location": location,
        "evidence_text": clean_display_text(text),
        "confidence": float(confidence),
        "extractor": extractor,
        "payload": payload or {},
    }


def entity(value, entity_type, role, source_url, location, text, confidence, payload=None):
    cleaned = clean_display_text(value)
    return {
        "value": cleaned,
        "entity_type": entity_type,
        "role": role or "",
        "source_url": source_url,
        "source_location": location,
        "evidence_text": clean_display_text(text),
        "confidence": float(confidence),
        "normalized_value": normalize_catalog_text(cleaned),
        "payload": payload or {},
    }


def append_unique_entity(entities, item):
    key = (
        item["entity_type"],
        item.get("role") or "",
        item.get("normalized_value") or normalize_catalog_text(item.get("value", "")),
    )
    if not key[2]:
        return
    if any(
        (
            current["entity_type"],
            current.get("role") or "",
            current.get("normalized_value") or normalize_catalog_text(current.get("value", "")),
        )
        == key
        for current in entities
    ):
        return
    entities.append(item)


def extract_book_entities(scraped_data, source_url):
    entities = []
    evidences = []
    title = clean_display_text(scraped_data.get("book_title", ""))
    if title:
        item = entity(
            title,
            CuratedEntityType.WORK,
            "book",
            source_url,
            f"{SOURCE_LOCATION_ROOT}.book_title",
            title,
            1.0,
            {"canonical_url": source_url},
        )
        append_unique_entity(entities, item)
        evidences.append(evidence(title, CuratedEntityType.WORK, "book", source_url, item["source_location"], title, 1.0, "title"))

    normalized = normalize_scraped_book(scraped_data)
    for contributor in normalized["contributors"]:
        role = contributor.get("role") or ContributorRole.AUTHOR
        entity_type = CuratedEntityType.ORGANIZATION if role == ContributorRole.PUBLISHER else CuratedEntityType.PERSON
        raw_value = contributor.get("raw_value") or contributor.get("name", "")
        location = f"{SOURCE_LOCATION_ROOT}.book_info" if role != ContributorRole.AUTHOR else f"{SOURCE_LOCATION_ROOT}.author"
        confidence = 0.95 if role != ContributorRole.AUTHOR else 0.9
        item = entity(contributor["name"], entity_type, role, source_url, location, raw_value, confidence)
        append_unique_entity(entities, item)
        evidences.append(evidence(contributor["name"], entity_type, role, source_url, location, raw_value, confidence, "metadata"))

    for series_name in normalized["series"]:
        item = entity(series_name, CuratedEntityType.SERIES, "series", source_url, f"{SOURCE_LOCATION_ROOT}.series", series_name, 0.95)
        append_unique_entity(entities, item)
    for category_name in normalized["categories"]:
        item = entity(category_name, CuratedEntityType.CATEGORY, "site_category", source_url, f"{SOURCE_LOCATION_ROOT}.book_type", category_name, 0.95)
        append_unique_entity(entities, item)

    for entry in extract_front_matter_entries(scraped_data.get("book_info", "")):
        key = entry.get("key") or ""
        if key not in PUBLICATION_KEYS:
            continue
        item = entity(
            entry["value"],
            CuratedEntityType.PUBLICATION_EVENT,
            key,
            source_url,
            f"{SOURCE_LOCATION_ROOT}.book_info",
            f"{entry.get('label', '')}: {entry['value']}",
            0.92,
        )
        append_unique_entity(entities, item)
        evidences.append(evidence(item["value"], item["entity_type"], key, source_url, item["source_location"], item["evidence_text"], 0.92, "front_matter_label"))

    cover = clean_display_text(scraped_data.get("cover", ""))
    if cover:
        item = entity(cover, CuratedEntityType.ASSET, "cover_image", source_url, f"{SOURCE_LOCATION_ROOT}.cover", cover, 0.95)
        append_unique_entity(entities, item)
        evidences.append(evidence(cover, CuratedEntityType.ASSET, "cover_image", source_url, item["source_location"], cover, 0.95, "cover"))

    extract_image_entities(scraped_data, source_url, entities, evidences)
    return entities, evidences


def extract_image_entities(scraped_data, source_url, entities, evidences):
    fragments = [
        ("main_content", scraped_data.get("main_content", "")),
        ("book_info", scraped_data.get("book_info", "")),
        ("dedication", scraped_data.get("dedication", "")),
    ]
    fragments.extend((f"content_items.{idx}.content", item.get("content", "")) for idx, item in enumerate(scraped_data.get("content_items", []) or []))
    for location, html in fragments:
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for index, image in enumerate(soup.find_all("img")):
            src = clean_display_text(image.get("src") or image.get("data-src") or "")
            if not src:
                continue
            payload = {"alt": clean_display_text(image.get("alt", "")), "index": index}
            item = entity(src, CuratedEntityType.ASSET, "content_image", source_url, f"{SOURCE_LOCATION_ROOT}.{location}", src, 0.88, payload)
            append_unique_entity(entities, item)
            evidences.append(evidence(src, CuratedEntityType.ASSET, "content_image", source_url, item["source_location"], src, 0.88, "content_image", payload))


def section(section_id, section_type, title, html, source_url, location, order, path=None, confidence=1.0, payload=None):
    return {
        "section_id": section_id,
        "section_type": section_type,
        "title": clean_display_text(title),
        "path": list(path or []),
        "source_url": source_url,
        "source_location": location,
        "html": html or "",
        "confidence": float(confidence),
        "sort_order": order,
        "payload": payload or {},
    }


def extract_sections(scraped_data, source_url):
    sections = []
    order = 0
    title = clean_display_text(scraped_data.get("book_title", ""))
    sections.append(section("title-page", CuratedSectionType.TITLE_PAGE, title, "", source_url, f"{SOURCE_LOCATION_ROOT}.book_title", order, [title]))
    order += 1
    if scraped_data.get("book_info"):
        sections.append(section("book-info", CuratedSectionType.BOOK_INFO, "বই তথ্য", scraped_data["book_info"], source_url, f"{SOURCE_LOCATION_ROOT}.book_info", order))
        order += 1
    if scraped_data.get("dedication"):
        sections.append(section("dedication", CuratedSectionType.DEDICATION, "উৎসর্গ", scraped_data["dedication"], source_url, f"{SOURCE_LOCATION_ROOT}.dedication", order))
        order += 1
    for index, item in enumerate(scraped_data.get("front_sections", []) or []):
        sid = stable_section_id("front", item.get("title", ""), index)
        sections.append(section(sid, CuratedSectionType.FRONT_MATTER, item.get("title", ""), item.get("html", ""), source_url, f"{SOURCE_LOCATION_ROOT}.front_sections.{index}", order, [item.get("title", "")], 0.9))
        order += 1
    if scraped_data.get("toc") or scraped_data.get("content_items"):
        sections.append(section("generated-toc", CuratedSectionType.GENERATED_TOC, "সূচিপত্র", "", source_url, "curated.generated_toc", order))
        order += 1
    residual_main = scraped_data.get("main_content", "")
    if residual_main:
        section_type = CuratedSectionType.BODY if not scraped_data.get("content_items") else CuratedSectionType.FRONT_MATTER
        sections.append(section("main-content", section_type, title or "মূল লেখা", residual_main, source_url, f"{SOURCE_LOCATION_ROOT}.main_content", order, [title or "মূল লেখা"], 0.84))
        order += 1
    for index, item in enumerate(scraped_data.get("content_items", []) or []):
        path = item.get("path") or [item.get("title", "")]
        sid = stable_section_id("body", " / ".join(path), index)
        sections.append(section(sid, CuratedSectionType.BODY, item.get("title", ""), item.get("content", ""), item.get("source_url") or source_url, f"{SOURCE_LOCATION_ROOT}.content_items.{index}", order, path, 0.93, {"type": item.get("type", "lesson"), "parent": item.get("parent")}))
        order += 1
    for index, item in enumerate(scraped_data.get("back_sections", []) or []):
        sid = stable_section_id("back", item.get("title", ""), index)
        sections.append(section(sid, CuratedSectionType.BACK_MATTER, item.get("title", ""), item.get("html", ""), source_url, f"{SOURCE_LOCATION_ROOT}.back_sections.{index}", order, [item.get("title", "")], 0.9))
        order += 1
    return sections


def build_projection(scraped_data, source_url):
    normalized = normalize_scraped_book(scraped_data)
    author_names = [
        item["name"]
        for item in normalized["contributors"]
        if item["role"] == ContributorRole.AUTHOR
    ]
    return {
        "book_title": normalized["title"] or clean_display_text(scraped_data.get("book_title", "")),
        "author": ", ".join(author_names) or scraped_data.get("author", ""),
        "series": scraped_data.get("series", ""),
        "book_type": scraped_data.get("book_type", ""),
        "cover": scraped_data.get("cover") or "",
        "main_content": scraped_data.get("main_content", ""),
        "book_info": scraped_data.get("book_info", ""),
        "dedication": scraped_data.get("dedication", ""),
        "front_sections": scraped_data.get("front_sections", []),
        "back_sections": scraped_data.get("back_sections", []),
        "toc": scraped_data.get("toc", []),
        "content_items": scraped_data.get("content_items", []),
        "output_folder": scraped_data.get("output_folder", ""),
        "source_url": source_url,
    }


def classify_structure(scraped_data):
    toc = scraped_data.get("toc") or []
    content_items = scraped_data.get("content_items") or []
    if any(entry.get("children") for entry in toc):
        return "nested_toc"
    if toc and content_items:
        return "flat_toc"
    if content_items:
        return "no_toc_heading_split"
    if plain_text_from_html(scraped_data.get("main_content", "")):
        return "single_flow_no_toc"
    return "incomplete"
