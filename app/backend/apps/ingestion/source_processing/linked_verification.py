from apps.ingestion.pipeline.curated_extractors import extract_sections
from apps.ingestion.pipeline.curated_pipeline import build_curated_document

from .collection_index import MAX_COLLECTION_DEPTH, linked_book_entries
from .content_text import canonical_text


def linked_snapshot(snapshot):
    return {
        key: snapshot[key]
        for key in (
            "source_url",
            "canonical_url",
            "raw_scrape_payload",
            "pages",
            "fetched_urls",
            "linked_index",
            "linked_books",
        )
        if key in snapshot
    } | {"source_structure": snapshot.get("manifest", {}).get("source_structure", {})}


def linked_source_result(snapshot):
    return {
        "document": build_curated_document(snapshot),
        "source_snapshot": {
            **snapshot,
            "manifest": {"source_structure": snapshot.get("source_structure", {})},
        },
    }


def missing_linked_text(snapshot, child):
    actual = {
        (item.get("linked_book"), item.get("linked_location")): canonical_text(
            item.get("content", "")
        )
        for item in snapshot.get("raw_scrape_payload", {}).get("content_items", [])
    }
    url = child.get("canonical_url", "")
    expected = extract_sections(child.get("raw_scrape_payload", {}), url)
    return any(
        text != actual.get((url, section["source_location"]))
        for section in expected
        if (text := canonical_text(section.get("html", "")))
    )


def linked_source_issues(snapshot, verify, lineage):
    if "linked_index" not in snapshot:
        raw = snapshot.get("raw_scrape_payload", {})
        if not raw.get("content_items") and linked_book_entries(
            raw.get("main_content", ""), snapshot.get("canonical_url", "")
        ):
            return ["Linked books must be collected and verified before publication."]
        return []
    url = snapshot.get("canonical_url", "")
    children = snapshot.get("linked_books", [])
    entries = linked_book_entries(snapshot["linked_index"], url)
    if len(lineage) >= MAX_COLLECTION_DEPTH or url in lineage:
        return ["Linked book collection contains a cycle or exceeds its depth limit."]
    if not entries or [entry.url for entry in entries] != [
        child.get("canonical_url") for child in children
    ]:
        return ["Not all linked books were collected in source order."]
    errors = []
    for child in children:
        if not verify(linked_source_result(child), (*lineage, url))["verified"]:
            errors.append(
                "A linked book does not provide complete verified reading content."
            )
        if missing_linked_text(snapshot, child):
            errors.append(
                "A linked book's collected text is missing from the combined book."
            )
    return errors
