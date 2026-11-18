"""Quality gate for curated books.

`book_quality_gate(curated)` returns `(ok: bool, reasons: list[str])`.
A book that fails the gate should be quarantined (set
`Book.state=ARCHIVED, review_state=REJECTED`) so it never appears in
published catalogues.

Rules are intentionally conservative: only books with zero real readable
content are rejected. Borderline cases pass and are surfaced via the
audit report instead.
"""

from apps.ingestion.services.normalization_modules.front_matter_text_rules import (
    plain_text_from_html,
)


MIN_BODY_TEXT_CHARS = 200


def book_quality_gate(curated):
    document = curated.get("document") or {}
    projection = curated.get("projection") or {}
    reasons = []

    structure_type = document.get("structure_type", "")
    if structure_type == "no_public_body":
        reasons.append("no_public_body_structure")

    body_sections = [
        section
        for section in document.get("sections") or []
        if section.get("section_type") == "body"
        and plain_text_from_html(section.get("html", "")).strip()
    ]
    if not body_sections:
        reasons.append("no_text_bearing_body_section")

    content_items = projection.get("content_items") or []
    content_chars = sum(
        len(plain_text_from_html(item.get("content", "")))
        for item in content_items
        if isinstance(item, dict)
    )
    main_text = plain_text_from_html(projection.get("main_content", "") or "")
    if content_chars < MIN_BODY_TEXT_CHARS and len(main_text) < MIN_BODY_TEXT_CHARS:
        reasons.append("body_text_below_minimum")

    # Drop duplicates while preserving order.
    seen = set()
    deduped = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            deduped.append(reason)
    return (not deduped), deduped
