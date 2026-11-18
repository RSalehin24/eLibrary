"""Diagnostic: run curated pipeline against live source site books and report defects.

Usage:
    cd app/backend && python -m diagnose_curation [N]

Reads URLs from ../../test-artifacts/source-site-audit-selection.json (first N entries).
Writes report to tmp/curation_diagnosis.json (relative to repo root).
"""
import json
import os
import sys
import traceback
from collections import Counter
from pathlib import Path

import django
from django.conf import settings as django_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# Use a dummy postgres URL; we never actually connect to the DB.
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/x")
django.setup()
# Replace with sqlite in-memory for any incidental ORM use.
django_settings.DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

from apps.ingestion.pipeline.curated_pipeline import curate_book_document
from apps.ingestion.services.normalization import plain_text_from_html


REPO_ROOT = Path(__file__).resolve().parents[2]
SELECTION = REPO_ROOT / "test-artifacts" / "source-site-audit-selection.json"
REPORT = REPO_ROOT / "tmp" / "curation_diagnosis.json"


def summarize(doc):
    projection = doc.get("projection") or {}
    sections = doc.get("sections") or []
    entities = doc.get("entities") or []
    validation = doc.get("validation") or {}
    section_types = Counter(s.get("section_type") for s in sections)
    body_sections = [s for s in sections if s.get("section_type") == "body"]
    body_with_text = [s for s in body_sections if plain_text_from_html(s.get("html", ""))]
    body_empty = [s for s in body_sections if not plain_text_from_html(s.get("html", ""))]
    contributor_roles = Counter(
        e.get("role") for e in entities if e.get("entity_type") in ("person", "organization")
    )
    return {
        "status": doc.get("status"),
        "structure_type": doc.get("structure_type"),
        "title": projection.get("book_title", ""),
        "author": projection.get("author", ""),
        "series": projection.get("series", ""),
        "categories": projection.get("book_type", ""),
        "cover": projection.get("cover", ""),
        "has_book_info": bool(plain_text_from_html(projection.get("book_info", ""))),
        "has_dedication": bool(plain_text_from_html(projection.get("dedication", ""))),
        "front_section_count": len(projection.get("front_sections") or []),
        "back_section_count": len(projection.get("back_sections") or []),
        "toc_count": len(projection.get("toc") or []),
        "content_item_count": len(projection.get("content_items") or []),
        "section_type_counts": dict(section_types),
        "body_with_text": len(body_with_text),
        "body_empty": len(body_empty),
        "body_empty_titles": [s.get("title") for s in body_empty][:5],
        "entity_count": len(entities),
        "contributor_roles": dict(contributor_roles),
        "asset_count": sum(1 for e in entities if e.get("entity_type") == "asset"),
        "validation_errors": validation.get("errors", []),
        "validation_warnings": validation.get("warnings", []),
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    entries = selection.get("selected", [])[:n]
    print(f"Diagnosing {len(entries)} books...")

    results = []
    error_counter = Counter()
    structure_counter = Counter()
    status_counter = Counter()

    for i, entry in enumerate(entries, 1):
        url = entry.get("source_url", "")
        title = entry.get("title", "")
        print(f"[{i}/{len(entries)}] {title}\n    {url}")
        try:
            result = curate_book_document(url)
            doc = result["document"]
            summary = summarize(doc)
            summary["source_url"] = url
            summary["expected_title"] = title
            summary["expected_authors"] = entry.get("author_line", "")
            results.append(summary)
            status_counter[summary["status"]] += 1
            structure_counter[summary["structure_type"]] += 1
            for err in summary["validation_errors"]:
                # bucket by first colon-prefixed category
                key = err.split(":", 1)[0].strip()
                error_counter[key] += 1
            print(
                f"    -> status={summary['status']} struct={summary['structure_type']} "
                f"body={summary['body_with_text']}+{summary['body_empty']}e "
                f"errors={len(summary['validation_errors'])}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    !! EXCEPTION: {exc}")
            tb = traceback.format_exc()
            results.append({
                "source_url": url,
                "expected_title": title,
                "exception": str(exc),
                "traceback_tail": tb.splitlines()[-6:],
            })
            error_counter["EXCEPTION"] += 1

    report = {
        "total": len(entries),
        "status_counts": dict(status_counter),
        "structure_counts": dict(structure_counter),
        "error_category_counts": dict(error_counter),
        "results": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport written to {REPORT}")
    print(f"Status: {dict(status_counter)}")
    print(f"Structures: {dict(structure_counter)}")
    print(f"Top error categories: {error_counter.most_common(15)}")


if __name__ == "__main__":
    main()
