from collections import Counter
from dataclasses import replace

from apps.ingestion.pipeline.book_manifest import (
    build_manifest_from_projection,
    disambiguate_duplicate_content_paths,
    duplicate_path_title,
    list_toc_structure_traits,
)
from apps.ingestion.pipeline.curated_extractors import extract_sections
from apps.ingestion.pipeline.curated_pipeline import build_curated_document
from apps.ingestion.pipeline.curated_source import build_source_snapshot
from apps.ingestion.pipeline.curated_validation import generated_toc_from_content_items
from apps.ingestion.pipeline.manifest_collection import ManifestCollector
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .collection_index import MAX_COLLECTION_DEPTH, linked_book_entries
from .content_text import canonical_text
from .linked_verification import linked_snapshot
from .policy import require_source_url, source_hosts
from .verification import source_verification


def skip_component_cover(url, folder, session):
    # Only the parent edition's cover belongs in its export directory.
    return ""


def component_items(child, title):
    snapshot = child["source_snapshot"]
    url = snapshot["canonical_url"]
    return [
        {
            "title": section["title"] or title,
            "content": section["html"],
            "type": "lesson",
            "parent": title,
            "path": [title, section["title"] or title],
            "source_url": section.get("source_url") or url,
            "linked_book": url,
            "linked_location": section["source_location"],
        }
        for section in extract_sections(snapshot["raw_scrape_payload"], url)
        if canonical_text(section.get("html", ""))
    ]


def collection_payload(snapshot, children):
    entries = linked_book_entries(
        snapshot["raw_scrape_payload"].get("main_content", ""),
        snapshot["canonical_url"],
    )
    items = []
    names: Counter[str] = Counter()
    for entry, child in zip(entries, children, strict=True):
        names[entry.title] += 1
        title = (
            duplicate_path_title(entry.title, names[entry.title])
            if names[entry.title] > 1
            else entry.title
        )
        items.extend(component_items(child, title))
    payload = {**snapshot["raw_scrape_payload"], "content_items": items, "toc": []}
    payload["toc"], payload["content_items"] = disambiguate_duplicate_content_paths(
        generated_toc_from_content_items(items), items
    )
    return payload


def combined_snapshot(snapshot, children):
    payload = collection_payload(snapshot, children)
    structure = {
        **snapshot["manifest"].get("source_structure", {}),
        "type": "sectioned_flat_lessons",
        "has_section_headings": True,
        "traits": list_toc_structure_traits(payload["toc"]),
        "topics_expected": len(payload["content_items"]),
        "topics_fetched": len(payload["content_items"]),
    }
    manifest = build_manifest_from_projection(
        snapshot["canonical_url"],
        payload,
        pages=snapshot["pages"],
        source_structure=structure,
    )
    return {
        **snapshot,
        "raw_scrape_payload": manifest["projection"],
        "manifest": manifest,
        "fetched_urls": sorted(
            {
                page["url"]
                for page in snapshot["pages"]
                if page.get("status") == "fetched"
            }
        ),
        "linked_index": snapshot["raw_scrape_payload"].get("main_content", ""),
        "linked_books": [
            linked_snapshot(child["source_snapshot"]) for child in children
        ],
    }


def require_component_content(result):
    evidence = source_verification(result)
    if evidence["verified"]:
        return
    codes = {
        "description_only": "source_description_only",
        "unknown_layout": "source_layout_unknown",
    }
    raise ExecutionFailure(
        FailureKind.TRANSIENT,
        codes.get(evidence["classification"], "source_content_unavailable"),
    )


class SourceDocumentCollector:
    def __init__(self, context, options):
        self.context = context
        self.options = options

    def components(self, entries, lineage):
        for entry in entries:
            require_source_url(entry.url, source_hosts())
        children = []
        for entry in entries:
            child = self.collect(entry.url, lineage)
            require_component_content(child)
            children.append(child)
        return children

    def collect(self, url, lineage=()):
        require_source_url(url, source_hosts())
        if url in lineage or len(lineage) >= MAX_COLLECTION_DEPTH:
            raise ExecutionFailure(FailureKind.TRANSIENT, "source_layout_unknown")
        options = (
            replace(self.options, cover_downloader=skip_component_cover)
            if lineage
            else self.options
        )
        snapshot = build_source_snapshot(
            ManifestCollector(self.context, options).collect(url)
        )
        raw = snapshot["raw_scrape_payload"]
        entries = (
            []
            if raw.get("content_items")
            else linked_book_entries(raw.get("main_content", ""), url)
        )
        if entries:
            children = self.components(entries, (*lineage, url))
            snapshot = combined_snapshot(snapshot, children)
        document = build_curated_document(snapshot)
        return {
            "document": document,
            "source_snapshot": snapshot,
            "projection": document["projection"],
            "status": document["status"],
            "validation": document["validation"],
        }
