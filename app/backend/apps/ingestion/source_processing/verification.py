from apps.ingestion.pipeline.curated_extractors import extract_sections
from apps.ingestion.pipeline.curated_validation import validate_document
from apps.ingestion.services.normalization import plain_text_from_html

from .classification import classification_evidence
from .content_text import canonical_text
from .linked_verification import linked_source_issues


def source_text_issues(document, snapshot):
    actual = {
        section.get("source_location"): canonical_text(section.get("html", ""))
        for section in document.get("sections", [])
    }
    expected = extract_sections(snapshot.get("raw_scrape_payload", {}), "")
    return [
        "Collected source text is missing from a book section."
        for section in expected
        if (text := canonical_text(section.get("html", "")))
        and text not in actual.get(section["source_location"], "")
    ]


def source_collection_issues(snapshot):
    structure = snapshot.get("manifest", {}).get("source_structure", {})
    errors = []
    if int(structure.get("topics_expected", 0)) > int(
        structure.get("topics_fetched", 0)
    ) or structure.get("content_incomplete"):
        errors.append("Not all available source chapters were collected.")
    if structure.get("toc_incomplete") or int(
        structure.get("source_total_pages", 0)
    ) > int(structure.get("fetched_total_pages", 0)):
        errors.append("Not all source contents pages were collected.")
    return errors


def source_verification(result, lineage=()):
    document = result.get("document", {})
    snapshot = result.get("source_snapshot", {})
    validation = validate_document(document, snapshot)
    structure = snapshot.get("manifest", {}).get("source_structure", {})
    pages = snapshot.get("pages", [])
    fetched = sum(page.get("status") == "fetched" for page in pages)
    expected = int(structure.get("topics_expected", 0))
    collected = int(structure.get("topics_fetched", 0))
    errors = list(validation["errors"])
    if not pages or not fetched:
        errors.append("No fetched source page is available for verification.")
    errors.extend(source_collection_issues(snapshot))
    errors.extend(
        warning for warning in validation["warnings"] if "not assigned" in warning
    )
    errors.extend(source_text_issues(document, snapshot))
    errors.extend(linked_source_issues(snapshot, source_verification, lineage))
    evidence = classification_evidence(snapshot)
    if not evidence["reading_content"]:
        errors.append("The source does not provide verified reading content.")
    return {
        **evidence,
        "verified": not errors,
        "source_pages": len(pages),
        "fetched_pages": fetched,
        "expected_chapters": expected,
        "collected_chapters": collected
        or sum(
            section.get("section_type") == "body"
            and bool(plain_text_from_html(section.get("html", "")))
            for section in document.get("sections", [])
        ),
        "issues": list(dict.fromkeys(errors))[:20],
    }
