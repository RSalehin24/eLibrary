"""Live integration tests for the EPUB pipeline against the spec reference books.

These tests make real HTTP requests to the source site.
They are marked ``live`` and are excluded from the normal unit-test run.

Run all live tests:
    docker exec compose-backend-1 sh -lc \\
        "cd /app && PYTHONPATH=/app DJANGO_SETTINGS_MODULE=config.settings \\
         pytest -c /workspace/tests/pytest.ini -m live /workspace/tests/backend/test_spec_books.py -v"

Run a single book (by keyword):
    ... pytest ... -k "hamlet"
"""
from __future__ import annotations

import pytest

from apps.ingestion.pipeline.curated_pipeline import curate_book_document
from apps.ingestion.services.normalization import plain_text_from_html

# ---------------------------------------------------------------------------
# Spec book definitions — each entry maps to one or more check functions.
# "checks" is a list of check-function names defined below.
# ---------------------------------------------------------------------------

SPEC_BOOKS = [
    {
        "id": "bhumika",
        "url": "https://www.example.com/books/ভূমিকা-প্রফুল্ল-রায়/",
        "name": "ভূমিকা — প্রফুল্ল রায়",
        "checks": ["no_cross_book_links_in_toc"],
    },
    {
        "id": "shankha_ghosh",
        "url": "https://www.example.com/books/শঙ্খ-ঘোষের-শ্রেষ্ঠ-কবিতা/",
        "name": "শঙ্খ ঘোষের শ্রেষ্ঠ কবিতা",
        "checks": ["toc_not_empty", "toc_has_parent_entries"],
    },
    {
        "id": "shopner_brishtimahal",
        "url": "https://www.example.com/books/স্বপ্নের-বৃষ্টিমহল-ওয়া/",
        "name": "স্বপ্নের বৃষ্টিমহল — ওয়াসিকা নুযহাত",
        "checks": ["has_dedication", "dedication_not_in_front_sections"],
    },
    {
        "id": "himu_baba",
        "url": "https://www.example.com/books/হিমুর-বাবার-কথামালা/",
        "name": "হিমুর বাবার কথামালা — হুমায়ূন আহমেদ",
        "checks": ["toc_not_empty", "no_artificial_chapter_split"],
    },
    {
        "id": "hamlet",
        "url": "https://www.example.com/books/hamlet-william-shakespeare/",
        "name": "Hamlet — William Shakespeare",
        "checks": ["english_labels"],
    },
    {
        "id": "2001",
        "url": "https://www.example.com/books/২০০১-আ-স্পেস-ওডিসি-আর্থার/",
        "name": "২০০১: A Space Odyssey — আর্থার ক্লার্ক",
        "checks": ["toc_not_empty", "has_book_info"],
    },
    {
        "id": "sherlock",
        "url": "https://www.example.com/books/শার্লক-হোমস-সমগ্র-১-অনুবা/",
        "name": "শার্লক হোমস সমগ্র ১",
        "checks": ["toc_not_empty", "has_book_info"],
    },
    {
        "id": "sidney_sheldon",
        "url": "https://www.example.com/books/সিডনি-সেলডন-রচনাসমগ্র-২/",
        "name": "সিডনি সেলডন রচনাসমগ্র ২",
        "checks": ["toc_not_empty"],
    },
    {
        "id": "ba12_satyajit",
        "url": "https://www.example.com/books/বাঃ-১২-সত্যজিৎ-রায়/",
        "name": "বাঃ ১২ — সত্যজিৎ রায়",
        "checks": ["toc_not_empty", "toc_has_parent_entries"],
    },
    {
        "id": "sati",
        "url": "https://www.example.com/books/সতী-দীনেশচন্দ্র-সেন/",
        "name": "সতী — দীনেশচন্দ্র সেন",
        "checks": ["has_book_info", "toc_not_empty"],
    },
    {
        "id": "lohit_kiran",
        "url": "https://www.example.com/books/লোহিতকিরণচ্ছটা/",
        "name": "লোহিতকিরণচ্ছটা",
        "checks": ["toc_not_empty", "has_book_info"],
    },
    {
        "id": "hat_chuye",
        "url": "https://www.example.com/books/হাত-ছুঁয়ে-ছুঁয়ে-দিয়েছ/",
        "name": "হাত ছুঁয়ে-ছুঁয়ে দিয়েছি সব",
        "checks": ["toc_not_empty", "has_book_info"],
    },
    {
        "id": "durga_rahasya",
        "url": "https://www.example.com/books/দুর্গরহস্য-শরদিন্দু-বন্/",
        "name": "দুর্গরহস্য — শরদিন্দু বন্দ্যোপাধ্যায়",
        "checks": ["toc_not_empty", "has_book_info"],
    },
]

# ---------------------------------------------------------------------------
# Check functions — each takes (projection) and returns a list of error strings.
# An empty list means the check passed.
# ---------------------------------------------------------------------------


def _count_toc_all(entries: list) -> int:
    total = len(entries)
    for e in entries:
        total += _count_toc_all(e.get("children") or [])
    return total


def check_no_cross_book_links_in_toc(projection: dict) -> list[str]:
    """No /books/... URLs may appear in TOC/content_items."""

    def _scan(entries):
        issues = []
        for e in entries:
            url = e.get("url", "") or ""
            if "/books/" in url and "/lessons/" not in url:
                issues.append(f"Cross-book link in TOC: {url}")
            issues.extend(_scan(e.get("children") or []))
        return issues

    toc = projection.get("toc") or []
    content_items = projection.get("content_items") or []
    return _scan(toc) + _scan(content_items)


def check_toc_not_empty(projection: dict) -> list[str]:
    toc = projection.get("toc") or []
    content_items = projection.get("content_items") or []
    main_content = projection.get("main_content", "") or ""
    if not toc and not content_items and not plain_text_from_html(main_content):
        return ["TOC is empty and no main content found"]
    return []


def check_has_dedication(projection: dict) -> list[str]:
    dedication = projection.get("dedication", "") or ""
    if not plain_text_from_html(dedication):
        return ["Expected a dedication but none was found"]
    return []


def check_dedication_not_in_front_sections(projection: dict) -> list[str]:
    issues = []
    dedication_text = plain_text_from_html(projection.get("dedication", "") or "").lower()
    for section in projection.get("front_sections") or []:
        title = (section.get("title") or "").lower()
        text = plain_text_from_html(section.get("html") or "").lower()
        if "উৎসর্গ" in title or "উৎসর্গ" in text:
            issues.append(
                f"Dedication keyword found in front section: '{section.get('title', '')[:60]}'"
            )
        if dedication_text and text and len(dedication_text) > 10:
            common = set(dedication_text.split()) & set(text.split())
            overlap = len(common) / max(len(dedication_text.split()), 1)
            if len(common) > 5 and overlap > 0.5:
                issues.append(
                    f"Front section content overlaps strongly with dedication: '{section.get('title', '')[:60]}'"
                )
    return issues


def check_toc_has_parent_entries(projection: dict) -> list[str]:
    """Nested TOC entries must preserve the parent title — not just show children."""
    for e in (projection.get("toc") or []) + (projection.get("content_items") or []):
        children = e.get("children") or []
        if children and not (e.get("title") or "").strip():
            return [
                f"Parent TOC entry has {len(children)} children but no title itself"
            ]
    return []


def check_english_labels(projection: dict) -> list[str]:
    """English books must use English labels in book_info — no Bengali keys."""
    book_info = projection.get("book_info", "") or ""
    if not book_info:
        return []
    bengali_labels = ["শিরোনাম:", "লেখক:", "অনুবাদক:", "প্রকাশক:", "সম্পাদক:"]
    text = plain_text_from_html(book_info)
    return [
        f"Bengali label '{label}' found in English book's book_info"
        for label in bengali_labels
        if label in text
    ]


def check_has_book_info(projection: dict) -> list[str]:
    book_info = projection.get("book_info", "") or ""
    if not plain_text_from_html(book_info):
        return ["Book info page is empty — must always have content"]
    return []


def check_no_artificial_chapter_split(projection: dict) -> list[str]:
    """Content items should not be excessively split from inline numbering."""
    content_items = projection.get("content_items") or []
    if len(content_items) > 50:
        return [
            f"Suspiciously high content item count ({len(content_items)}) — possible artificial split"
        ]
    return []


_CHECKS = {
    "no_cross_book_links_in_toc": check_no_cross_book_links_in_toc,
    "toc_not_empty": check_toc_not_empty,
    "has_dedication": check_has_dedication,
    "dedication_not_in_front_sections": check_dedication_not_in_front_sections,
    "toc_has_parent_entries": check_toc_has_parent_entries,
    "english_labels": check_english_labels,
    "has_book_info": check_has_book_info,
    "no_artificial_chapter_split": check_no_artificial_chapter_split,
}

# ---------------------------------------------------------------------------
# Parametrized live tests
# ---------------------------------------------------------------------------

_BOOK_IDS = [b["id"] for b in SPEC_BOOKS]
_BOOK_MAP = {b["id"]: b for b in SPEC_BOOKS}


def _curate(url: str) -> dict:
    result = curate_book_document(url)
    doc = result["document"]
    return result.get("projection") or doc.get("projection") or {}


@pytest.mark.live
@pytest.mark.parametrize("book_id", _BOOK_IDS)
def test_spec_book(book_id: str) -> None:
    """Run all checks for a single spec reference book."""
    book = _BOOK_MAP[book_id]
    projection = _curate(book["url"])

    all_issues: list[str] = []
    for check_id in book["checks"]:
        fn = _CHECKS.get(check_id)
        assert fn is not None, f"Unknown check: {check_id}"
        issues = fn(projection)
        for issue in issues:
            all_issues.append(f"[{check_id}] {issue}")

    assert not all_issues, (
        f"{book['name']}\n" + "\n".join(f"  • {i}" for i in all_issues)
    )
