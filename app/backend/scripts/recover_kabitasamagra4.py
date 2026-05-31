"""
Recovery script for কবিতাসমগ্র ৪ (request-048d8e0e)

The book lost 102 topic HTML items due to a corrupt re-scrape.
This script:
 1. Fetches the 102 missing topic pages from the source site.
 2. Re-extracts front_sections from the book's landing page.
 3. Rebuilds book.content_items (182 items) and book.toc (6 lessons).
 4. Regenerates the EPUB + HTML exports.
"""

import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
django.setup()

import requests  # noqa: E402
from collections import OrderedDict  # noqa: E402

from apps.common.text import normalize_catalog_text  # noqa: E402
from apps.ingestion.pipeline.book_manifest import (  # noqa: E402
    SourceFetchContext,
    fetch_content_item,
    extract_entry_content_html,
    extract_main_content_segments,
    split_leading_front_sections,
    _drop_inline_toc_front_sections,
    _drop_chapter_title_front_sections,
    dedupe_structured_sections,
)
from apps.ingestion.pipeline.curated_persistence import CuratedBookDocument  # noqa: E402
from apps.ingestion.services.legacy_adapter import generate_exports  # noqa: E402
from apps.ingestion.services.submissions_support.persistence import (  # noqa: E402
    export_payload_from_book,
)
from apps.processing.models import BookCreationRequest  # noqa: E402

# ──────────────────────────────────────────────────────────────────────────────
# 0.  Locate the request and book
# ──────────────────────────────────────────────────────────────────────────────
r = BookCreationRequest.objects.filter(pk__startswith="request-048d8e0e").first()
if not r:
    print("ERROR: request-048d8e0e not found")
    sys.exit(1)

book = r.linked_book
print(f"Book: {book.title}")
print(f"Current content_items: {len(book.content_items or [])}")
print(f"Current toc lessons:   {len(book.toc or [])}")

# ──────────────────────────────────────────────────────────────────────────────
# 1.  Load the 191-section document (the "gold" scrape)
# ──────────────────────────────────────────────────────────────────────────────
good_doc = None
for doc in CuratedBookDocument.objects.filter(book=book).order_by("-created_at"):
    ss = doc.source_snapshot or {}
    mf = ss.get("manifest") or {}
    sections = mf.get("sections") or []
    if len(sections) == 191:
        good_doc = doc
        break

if not good_doc:
    print("ERROR: 191-section CuratedBookDocument not found")
    sys.exit(1)

canonical_url = good_doc.canonical_url
print(f"Using doc {str(good_doc.id)[:8]} ({len(good_doc.source_snapshot['manifest']['sections'])} sections)")
print(f"Canonical URL: {canonical_url}")

all_sections = good_doc.source_snapshot["manifest"]["sections"]
body_sections = [s for s in all_sections if s.get("section_type") == "body"]
print(f"Body sections: {len(body_sections)}")

# ──────────────────────────────────────────────────────────────────────────────
# 2.  Create scrape context (loads auth cookies)
# ──────────────────────────────────────────────────────────────────────────────
session = requests.Session()
ctx = SourceFetchContext(session, sleep_seconds=0.5)
limits = {"max_content_chars": None, "max_nodes": None}
print("Auth cookies loaded.")

# ──────────────────────────────────────────────────────────────────────────────
# 3.  Identify existing vs missing topics
# ──────────────────────────────────────────────────────────────────────────────
existing_items = {
    normalize_catalog_text(ci.get("title", "")): ci
    for ci in (book.content_items or [])
}
missing_sections = [
    s for s in body_sections
    if normalize_catalog_text(s.get("title", "")) not in existing_items
]
print(f"Existing topics: {len(existing_items)}, Missing: {len(missing_sections)}")

# ──────────────────────────────────────────────────────────────────────────────
# 4.  Fetch the 102 missing topic pages
# ──────────────────────────────────────────────────────────────────────────────
new_items = {}
failed = []
for i, sec in enumerate(missing_sections):
    url = sec.get("source_url", "")
    title = sec.get("title", "")
    path = sec.get("path") or [title]
    if not url:
        print(f"  [{i+1}/{len(missing_sections)}] SKIP (no URL): [{title}]")
        failed.append(title)
        continue

    node = {"url": url, "title": title, "type": "topic"}
    item = fetch_content_item(node, path, ctx, limits)
    if item:
        norm = normalize_catalog_text(item["title"])
        new_items[norm] = item
        chars = len(item.get("content", ""))
        print(f"  [{i+1}/{len(missing_sections)}] OK: [{title[:40]}] {chars} chars")
    else:
        print(f"  [{i+1}/{len(missing_sections)}] EMPTY: [{title[:40]}]")
        failed.append(title)

print(f"\nFetched: {len(new_items)}, Failed/empty: {len(failed)}")
if failed:
    print("Failed titles:")
    for t in failed:
        print(f"  - {t}")

# ──────────────────────────────────────────────────────────────────────────────
# 5.  Fetch front_sections from the landing page
# ──────────────────────────────────────────────────────────────────────────────
print(f"\nFetching landing page: {canonical_url}")
landing_soup = ctx.fetch_soup(canonical_url, kind="landing", title=book.title, cache=False)
front_sections = []
if landing_soup:
    landing_main = extract_entry_content_html(landing_soup, book.title)
    _, _, residual_main = extract_main_content_segments(landing_main or "")
    leading, _ = split_leading_front_sections(residual_main or "", has_explicit_body=True)
    front_sections = list(leading)
    print(f"  Extracted {len(front_sections)} front sections from landing page")
    for fs in front_sections:
        html_chars = len(fs.get("html", ""))
        print(f"    [{fs.get('title', '(no title)')}] html_chars={html_chars}")
    landing_soup.decompose()
else:
    print("  WARNING: Failed to fetch landing page — front_sections will be empty")

# ──────────────────────────────────────────────────────────────────────────────
# 6.  Build the full content_items and toc (ordered by 191-doc section order)
# ──────────────────────────────────────────────────────────────────────────────
all_items_by_norm = dict(existing_items)
all_items_by_norm.update(new_items)

# Build toc from 191-doc section ordering
lesson_children = OrderedDict()  # lesson_name → list of toc children
for s in body_sections:
    path = s.get("path") or []
    lesson_name = path[0] if path else ""
    topic_title = path[1] if len(path) > 1 else s.get("title", "")
    if not lesson_name:
        continue
    norm = normalize_catalog_text(topic_title)
    item = all_items_by_norm.get(norm)
    child_entry = {
        "path": list(path),
        "type": "topic",
        "title": topic_title,
        "source_url": (item or {}).get("source_url", s.get("source_url", "")),
        "has_content": bool((item or {}).get("content")),
    }
    if lesson_name not in lesson_children:
        lesson_children[lesson_name] = []
    lesson_children[lesson_name].append(child_entry)

new_toc = [
    {
        "path": [lesson_name],
        "type": "lesson",
        "title": lesson_name,
        "children": children,
    }
    for lesson_name, children in lesson_children.items()
]

# Build ordered content_items list
ordered_items = []
missing_from_all = []
for s in body_sections:
    path = s.get("path") or []
    topic_title = path[1] if len(path) > 1 else s.get("title", "")
    norm = normalize_catalog_text(topic_title)
    item = all_items_by_norm.get(norm)
    if item:
        ordered_items.append(item)
    else:
        missing_from_all.append(s.get("title", "?"))

print(f"\nRebuilt:")
print(f"  content_items: {len(ordered_items)}/182")
print(f"  toc lessons:   {len(new_toc)}")
for lesson_name, children in lesson_children.items():
    print(f"    [{lesson_name}]: {len(children)} topics")
if missing_from_all:
    print(f"  Still missing from all sources: {len(missing_from_all)}")
    for t in missing_from_all[:5]:
        print(f"    - {t}")

# ──────────────────────────────────────────────────────────────────────────────
# 7.  Apply front_section filtering using the COMPLETE toc
# ──────────────────────────────────────────────────────────────────────────────
if new_toc and front_sections:
    front_sections = _drop_inline_toc_front_sections(front_sections)
    front_sections = _drop_chapter_title_front_sections(front_sections, new_toc)

print(f"\nFront sections after filtering: {len(front_sections)}")
for fs in front_sections:
    print(f"  [{fs.get('title', '(no title)')}] html_chars={len(fs.get('html',''))}")

# ──────────────────────────────────────────────────────────────────────────────
# 8.  Update book model in DB
# ──────────────────────────────────────────────────────────────────────────────
print("\nUpdating book.content_items and book.toc in DB...")
book.content_items = ordered_items
book.toc = new_toc

# Also store front_sections in raw_scrape_payload so future regen works
rsp = dict(book.raw_scrape_payload or {})
rsp["front_sections"] = front_sections
book.raw_scrape_payload = rsp

book.save(update_fields=["content_items", "toc", "raw_scrape_payload", "updated_at"])
print("  Saved.")

# ──────────────────────────────────────────────────────────────────────────────
# 9.  Regenerate EPUB and HTML exports
# ──────────────────────────────────────────────────────────────────────────────
print("\nRegenerating EPUB + HTML exports...")
scraped_data = {
    "output_folder": rsp.get("output_folder", "/storage/media/scraped-books/\u0995\u09ac\u09bf\u09a4\u09be\u09b8\u09ae\u0997\u09cd\u09b0_\u09ea"),
    "front_sections": front_sections,
    "back_sections": [],
    "cover": rsp.get("cover", ""),
    "cover_source_url": rsp.get("cover_source_url", ""),
}
book.refresh_from_db()  # re-load after save
export_payload = export_payload_from_book(book, scraped_data)
generate_exports(export_payload)
print("Done! EPUB and HTML regenerated successfully.")
print(f"\nSummary:")
print(f"  content_items: {len(book.content_items)}")
print(f"  toc lessons:   {len(book.toc)}")
print(f"  front_sections in export: {len(export_payload.get('front_sections', []))}")
