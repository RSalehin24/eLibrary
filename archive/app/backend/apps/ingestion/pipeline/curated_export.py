from copy import deepcopy

from apps.ingestion.pipeline.book_manifest import manifest_to_projection


def is_curated_document(payload):
    return isinstance(payload, dict) and "projection" in payload and "validation" in payload


def curated_document_to_legacy_payload(document):
    manifest = document.get("manifest") or {}
    if manifest:
        projection = {
            **manifest_to_projection(manifest),
            **deepcopy(document.get("projection") or {}),
        }
    else:
        projection = deepcopy(document.get("projection") or {})
    projection.setdefault("book_title", document.get("book", {}).get("clean_title", ""))
    projection.setdefault("author", "")
    projection.setdefault("series", "")
    projection.setdefault("book_type", "")
    projection.setdefault("cover", "")
    projection.setdefault("main_content", "")
    projection.setdefault("book_info", "")
    projection.setdefault("dedication", "")
    projection.setdefault("front_sections", [])
    projection.setdefault("back_sections", [])
    projection.setdefault("toc", [])
    projection.setdefault("content_items", [])
    projection.setdefault("output_folder", "")
    if manifest:
        projection["canonical_manifest"] = manifest
    projection["canonical_sections"] = deepcopy(document.get("sections") or [])
    projection["curated_document_version"] = document.get("schema_version", "")
    projection["curated_document_status"] = document.get("status", "")
    return projection


def curated_document_with_projection(document, projection):
    merged_projection = {
        **(document.get("projection") or {}),
        **(projection or {}),
    }
    return {
        **document,
        **merged_projection,
        "projection": merged_projection,
    }
