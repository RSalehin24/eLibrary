"""
End-to-end regression harness for ~300 example.com books.

Driven by ``tests/scripts/regression_curate_300.sh`` (which execs this script
inside the backend container). For each URL drawn from
``test-artifacts/source-site-audit-selection.json`` (or a shard file via
``--selection``) the harness:

1. scrapes the book via ``processing_source.scrape_book_high_fidelity``;
2. exports HTML + EPUB into a per-book folder under
   ``--export-root`` (default ``/app/storage/regression-300/exports``);
3. runs :func:`apps.ingestion.pipeline.epub_structure_audit.audit_epub_structure`
   to validate spine order, nav/toc parity, no nav self-link, and
   no blank pages.

State is persisted after every URL to ``--state`` (default
``/app/storage/regression-300/state.json``) so reruns skip URLs already
recorded with verdict ``ok``. Pass ``--retry-failed`` to re-attempt URLs
previously marked as failed; otherwise they are skipped too (so the harness
is fully resumable across crashes / container restarts).

Exit code: ``0`` if every attempted URL passed the audit; ``1`` if any
URL failed. The detailed per-URL results live in the state JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import List, Optional

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.ingestion.pipeline.epub_structure_audit import audit_epub_structure
from apps.processing import source as processing_source


DEFAULT_SELECTION = Path("/workspace/test-artifacts/source-site-audit-selection.json")
DEFAULT_EXPORT_ROOT = Path("/app/storage/regression-300/exports")
DEFAULT_STATE_PATH = Path("/app/storage/regression-300/state.json")
DEFAULT_LIMIT = 300


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--purge-exports",
        action="store_true",
        help="Delete each per-book export folder once the audit passes "
        "(keeps disk usage bounded during a 300-book run).",
    )
    return parser.parse_args(argv)


def load_selection(path: Path, limit: int) -> List[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "selected" in payload:
        entries = payload["selected"]
    elif isinstance(payload, list):
        entries = payload
    else:
        raise SystemExit(f"selection file {path} has unexpected shape")
    urls: List[dict] = []
    for entry in entries:
        url = entry.get("source_url") or entry.get("url")
        if not url:
            continue
        urls.append(
            {
                "id": entry.get("id") or url,
                "source_url": url,
                "title": entry.get("title") or entry.get("local_book_title") or "",
            }
        )
        if len(urls) >= limit:
            break
    return urls


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"results": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def safe_folder_name(index: int, title: str) -> str:
    import re

    cleaned = re.sub(r"[^\w\u0980-\u09FF-]+", "_", title or "book", flags=re.UNICODE)
    cleaned = cleaned.strip("._")[:80] or "book"
    return f"{index:04d}_{cleaned}"


def export_one(entry: dict, index: int, export_root: Path) -> dict:
    started_at = time.time()
    scraped_data = processing_source.scrape_book_high_fidelity(entry["source_url"])
    if not isinstance(scraped_data, dict):
        raise AssertionError("scrape returned no structured payload")

    export_dir = export_root / safe_folder_name(index, scraped_data.get("book_title") or entry.get("title") or "book")
    export_dir.mkdir(parents=True, exist_ok=True)

    # Move any cover image fetched by the scraper into the export dir so
    # create_epub can resolve it.
    cover_name = scraped_data.get("cover")
    original_dir = Path(scraped_data.get("output_folder") or "")
    if cover_name and original_dir.exists():
        original_cover = original_dir / str(cover_name)
        if original_cover.exists():
            shutil.copy2(original_cover, export_dir / original_cover.name)
    scraped_data["output_folder"] = str(export_dir)

    processing_source.generate_exports(scraped_data)
    epub_candidates = sorted(export_dir.glob("*.epub"))
    if not epub_candidates:
        raise AssertionError(f"no EPUB produced in {export_dir}")
    epub_path = epub_candidates[0]
    audit = audit_epub_structure(epub_path)

    return {
        "verdict": "ok" if audit.ok else "failed",
        "epub_path": str(epub_path),
        "export_dir": str(export_dir),
        "audit": audit.to_dict(),
        "elapsed_seconds": round(time.time() - started_at, 2),
    }


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    args.export_root.mkdir(parents=True, exist_ok=True)
    state = load_state(args.state)
    results: dict = state.setdefault("results", {})

    entries = load_selection(args.selection, args.limit)
    total = len(entries)
    print(f"[regression-300] loaded {total} URLs from {args.selection}", flush=True)

    new_pass = 0
    new_fail = 0
    skipped = 0
    started_at = time.time()

    for index, entry in enumerate(entries, start=1):
        url = entry["source_url"]
        existing = results.get(url)
        if existing:
            verdict = existing.get("verdict")
            if verdict == "ok" or (verdict == "failed" and not args.retry_failed):
                skipped += 1
                continue

        print(
            f"[regression-300] [{index}/{total}] scraping {url}",
            flush=True,
        )
        try:
            outcome = export_one(entry, index, args.export_root)
        except Exception as exc:  # broad — harness is best-effort
            outcome = {
                "verdict": "failed",
                "error": str(exc),
                "traceback": traceback.format_exc(limit=20),
            }

        outcome["title"] = entry.get("title", "")
        outcome["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        results[url] = outcome
        save_state(args.state, state)

        if outcome["verdict"] == "ok":
            new_pass += 1
            if args.purge_exports:
                shutil.rmtree(outcome.get("export_dir", ""), ignore_errors=True)
            print(
                f"[regression-300] [{index}/{total}] OK ({outcome.get('elapsed_seconds')}s)",
                flush=True,
            )
        else:
            new_fail += 1
            errors = outcome.get("audit", {}).get("errors") or [outcome.get("error", "")]
            print(
                f"[regression-300] [{index}/{total}] FAIL: {errors[:3]}",
                flush=True,
            )

    summary = {
        "total_urls": total,
        "ran_passed": new_pass,
        "ran_failed": new_fail,
        "skipped_already_recorded": skipped,
        "elapsed_seconds": round(time.time() - started_at, 2),
        "state_path": str(args.state),
    }
    state["last_summary"] = summary
    save_state(args.state, state)
    print(json.dumps({"regression_300_summary": summary}, ensure_ascii=False), flush=True)

    # Overall exit: 1 if any URL in the state is failed AND was attempted in
    # this run, OR if there are no successful results. Otherwise 0.
    any_failed = any(item.get("verdict") == "failed" for item in results.values())
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
