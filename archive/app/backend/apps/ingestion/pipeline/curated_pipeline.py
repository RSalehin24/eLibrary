from apps.catalog.models import CuratedDocumentStatus
from apps.common.text import clean_display_text
from apps.ingestion.pipeline.curated_extractors import (
    build_projection,
    classify_structure,
    extract_book_entities,
    extract_sections,
)
from apps.ingestion.pipeline.curated_source import (
    CURATED_DOCUMENT_SCHEMA_VERSION,
    build_source_snapshot,
    fetch_source_pages,
)
from apps.ingestion.pipeline.curated_validation import (
    generated_toc_from_content_items,
    validate_document,
)
from apps.ingestion.pipeline.book_manifest import (
    build_manifest_from_legacy_payload,
    manifest_to_projection,
)
from apps.ingestion.services.normalization import promote_leading_front_matter


def normalize_scraped_payload(scraped_data):
    if not isinstance(scraped_data, dict):
        return {}
    normalized = dict(scraped_data)
    promoted_book_info, cleaned_main_content = promote_leading_front_matter(
        normalized.get("book_info", ""),
        normalized.get("main_content", ""),
    )
    normalized["book_info"] = promoted_book_info
    normalized["main_content"] = cleaned_main_content
    if normalized.get("content_items") and not normalized.get("toc"):
        normalized["toc"] = generated_toc_from_content_items(normalized["content_items"])
    return normalized


def build_book_metadata(scraped_data, canonical_url, structure_type):
    title = clean_display_text(scraped_data.get("book_title", ""))
    return {
        "canonical_url": canonical_url,
        "archive_title": title,
        "page_title": title,
        "clean_title": title,
        "subtitle": "",
        "alternate_title": "",
        "original_title": "",
        "volume_or_part": "",
        "collection_title": "",
        "incomplete_marker": structure_type == "incomplete",
    }


def empty_invalid_document(source_url, snapshot):
    document = {
        "schema_version": CURATED_DOCUMENT_SCHEMA_VERSION,
        "source_url": source_url,
        "canonical_url": source_url,
        "status": CuratedDocumentStatus.INVALID,
        "structure_type": "incomplete",
        "book": build_book_metadata({}, source_url, "incomplete"),
        "entities": [],
        "sections": [],
        "evidence": [],
        "assets": [],
        "projection": {
            "book_title": "",
            "author": "",
            "series": "",
            "book_type": "",
            "cover": "",
            "main_content": "",
            "book_info": "",
            "dedication": "",
            "front_sections": [],
            "back_sections": [],
            "toc": [],
            "content_items": [],
            "output_folder": "",
            "source_url": source_url,
        },
        "validation": {},
    }
    validation = validate_document(document, snapshot)
    document["validation"] = validation
    document["status"] = validation["status"]
    return document


def build_curated_document(snapshot):
    source_url = snapshot.get("source_url", "")
    canonical_url = snapshot.get("canonical_url") or source_url
    manifest = snapshot.get("manifest") or {}
    if manifest:
        projection = normalize_scraped_payload(manifest_to_projection(manifest))
        manifest = {**manifest, "projection": projection}
        source_structure = manifest.get("source_structure") or {}
        structure_type = source_structure.get("type") or classify_structure(projection)
        entities = manifest.get("entities") or []
        evidences = manifest.get("evidence") or []
        sections = manifest.get("sections") or extract_sections(projection, canonical_url)
        assets = manifest.get("assets") or [
            item for item in entities if item.get("entity_type") == "asset"
        ]
        document = {
            "schema_version": manifest.get("schema_version", CURATED_DOCUMENT_SCHEMA_VERSION),
            "source_url": source_url,
            "canonical_url": canonical_url,
            "status": CuratedDocumentStatus.DRAFT,
            "structure_type": structure_type,
            "book": build_book_metadata(projection, canonical_url, structure_type),
            "entities": entities,
            "sections": sections,
            "evidence": evidences,
            "assets": assets,
            "projection": projection,
            "manifest": manifest,
            "source_snapshot_ref": {
                "fetched_urls": snapshot.get("fetched_urls", []),
                "page_count": len(snapshot.get("pages", [])),
            },
            "validation": {},
        }
        document.update(
            {
                key: projection.get(key)
                for key in (
                    "book_title",
                    "author",
                    "series",
                    "book_type",
                    "cover",
                    "main_content",
                    "book_info",
                    "dedication",
                    "front_sections",
                    "back_sections",
                    "toc",
                    "content_items",
                    "output_folder",
                )
            }
        )
        validation = validate_document(document, {**snapshot, "raw_scrape_payload": projection})
        document["validation"] = validation
        document["status"] = validation["status"]
        return document

    scraped_data = normalize_scraped_payload(snapshot.get("raw_scrape_payload") or {})
    snapshot = {**snapshot, "raw_scrape_payload": scraped_data}
    if not scraped_data:
        return empty_invalid_document(canonical_url, snapshot)

    structure_type = classify_structure(scraped_data)
    entities, evidences = extract_book_entities(scraped_data, canonical_url)
    sections = extract_sections(scraped_data, canonical_url)
    projection = build_projection(scraped_data, canonical_url)
    assets = [item for item in entities if item.get("entity_type") == "asset"]
    document = {
        "schema_version": CURATED_DOCUMENT_SCHEMA_VERSION,
        "source_url": source_url,
        "canonical_url": canonical_url,
        "status": CuratedDocumentStatus.DRAFT,
        "structure_type": structure_type,
        "book": build_book_metadata(scraped_data, canonical_url, structure_type),
        "entities": entities,
        "sections": sections,
        "evidence": evidences,
        "assets": assets,
        "projection": projection,
        "source_snapshot_ref": {
            "fetched_urls": snapshot.get("fetched_urls", []),
            "page_count": len(snapshot.get("pages", [])),
        },
        "validation": {},
    }
    document.update(
        {
            key: projection.get(key)
            for key in (
                "book_title",
                "author",
                "series",
                "book_type",
                "cover",
                "main_content",
                "book_info",
                "dedication",
                "front_sections",
                "back_sections",
                "toc",
                "content_items",
                "output_folder",
            )
        }
    )
    validation = validate_document(document, snapshot)
    document["validation"] = validation
    document["status"] = validation["status"]
    return document


def curate_scraped_book_data(source_url, scraped_data):
    source_pages = build_manifest_from_legacy_payload(source_url, scraped_data)
    snapshot = build_source_snapshot(source_pages)
    document = build_curated_document(snapshot)
    return {
        "document": document,
        "source_snapshot": snapshot,
        "projection": document["projection"],
        "status": document["status"],
        "validation": document["validation"],
    }


def curate_book_document(source_url, *, content_limits=None, page_cache=None):
    source_pages = fetch_source_pages(source_url, content_limits=content_limits, page_cache=page_cache)
    snapshot = build_source_snapshot(source_pages)
    document = build_curated_document(snapshot)
    return {
        "document": document,
        "source_snapshot": snapshot,
        "projection": document["projection"],
        "status": document["status"],
        "validation": document["validation"],
    }
