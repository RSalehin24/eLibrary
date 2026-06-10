import json
import os
import re
import shutil
import time
import traceback
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import django
from bs4 import BeautifulSoup


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.common.source_site_batch_audit import refresh_source_archive
from apps.ingestion.models import SourceCatalogEntry
from apps.processing import source as processing_source


DESIRED_SUCCESS_COUNT = 200
CANDIDATE_LIMIT = 260
ARCHIVE_REFRESH_PAGES = 25
REPORT_DIR = Path("/app/storage/live-validation-report")
EXPORT_ROOT = Path("/app/storage/live-validation")


def plain_text_from_html(html):
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def safe_folder_name(index, title):
    cleaned = re.sub(r"[^\w\u0980-\u09FF-]+", "_", title or "book", flags=re.UNICODE)
    cleaned = cleaned.strip("._")[:80] or "book"
    return f"{index:03d}_{cleaned}"


def ensure_export_dir(index, title):
    export_dir = EXPORT_ROOT / safe_folder_name(index, title)
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def copy_cover_if_present(scraped_data, export_dir):
    cover_name = scraped_data.get("cover")
    if not cover_name:
        return

    original_dir = Path(scraped_data.get("output_folder") or "")
    if not original_dir.exists():
        return

    original_cover = original_dir / str(cover_name)
    if not original_cover.exists():
        return

    shutil.copy2(original_cover, export_dir / original_cover.name)


def classify_structure(scraped_data):
    toc = scraped_data.get("toc", []) or []
    content_items = scraped_data.get("content_items", []) or []
    front_sections = scraped_data.get("front_sections", []) or []
    back_sections = scraped_data.get("back_sections", []) or []
    main_content = plain_text_from_html(scraped_data.get("main_content", ""))
    nested = any(entry.get("children") for entry in toc)

    labels = set()
    if nested:
        labels.add("nested_toc")
    elif toc:
        labels.add("flat_toc")
    else:
        labels.add("no_toc")

    if content_items:
        labels.add("structured_content_items")
    elif main_content:
        labels.add("single_flow_main_content")

    if front_sections:
        labels.add("front_sections")
    if back_sections:
        labels.add("back_sections")

    return sorted(labels)


def validate_generated_files(export_dir, scraped_data):
    html_path = export_dir / "book.html"
    epub_files = sorted(export_dir.glob("*.epub"))
    if not html_path.exists():
        raise AssertionError(f"missing HTML preview: {html_path}")
    if not epub_files:
        raise AssertionError(f"missing EPUB export in {export_dir}")

    html_text = html_path.read_text(encoding="utf-8")
    if "<html" not in html_text.lower():
        raise AssertionError(f"invalid HTML preview: {html_path}")

    if scraped_data.get("toc") and "toc-section" not in html_text:
        raise AssertionError(f"missing TOC section for structured book: {html_path}")
    if scraped_data.get("front_sections") and "front-section" not in html_text:
        raise AssertionError(f"missing front sections for structured book: {html_path}")
    if scraped_data.get("back_sections") and "back-section" not in html_text:
        raise AssertionError(f"missing back sections for structured book: {html_path}")

    epub_path = epub_files[0]
    with zipfile.ZipFile(epub_path) as archive:
        names = set(archive.namelist())
        if "mimetype" not in names:
            raise AssertionError(f"EPUB missing mimetype entry: {epub_path}")
        if not any(name.endswith((".xhtml", ".html")) for name in names):
            raise AssertionError(f"EPUB missing HTML/XHTML payload: {epub_path}")
        if not any("nav" in name.lower() for name in names):
            raise AssertionError(f"EPUB missing navigation document: {epub_path}")

    return {
        "html_path": str(html_path),
        "epub_path": str(epub_path),
    }


def fetch_candidate_entries(limit):
    queryset = (
        SourceCatalogEntry.objects.filter(source_url__contains="/books/")
        .order_by("id")
    )
    return list(queryset[:limit])


def main():
    started_at = time.time()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)

    print(
        json.dumps(
            {
                "stage": "refresh_archive",
                "max_pages": ARCHIVE_REFRESH_PAGES,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    refresh_source_archive(max_pages=ARCHIVE_REFRESH_PAGES)

    entries = fetch_candidate_entries(CANDIDATE_LIMIT)
    if len(entries) < DESIRED_SUCCESS_COUNT:
        raise RuntimeError(
            f"expected at least {DESIRED_SUCCESS_COUNT} source entries after refresh, got {len(entries)}"
        )

    successes = []
    failures = []
    structure_counts = Counter()
    examples_by_structure = defaultdict(list)

    for index, entry in enumerate(entries, start=1):
        if len(successes) >= DESIRED_SUCCESS_COUNT:
            break

        print(
            json.dumps(
                {
                    "stage": "scrape_export",
                    "candidate_index": index,
                    "successes": len(successes),
                    "url": entry.source_url,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

        try:
            scraped_data = processing_source.scrape_book_high_fidelity(entry.source_url)
            if not isinstance(scraped_data, dict):
                raise AssertionError("scrape returned no structured payload")

            export_dir = ensure_export_dir(index, scraped_data.get("book_title", ""))
            copy_cover_if_present(scraped_data, export_dir)
            scraped_data["output_folder"] = str(export_dir)

            processing_source.generate_exports(scraped_data)
            generated_files = validate_generated_files(export_dir, scraped_data)
            structures = classify_structure(scraped_data)

            result = {
                "index": index,
                "source_url": entry.source_url,
                "title": scraped_data.get("book_title", ""),
                "structures": structures,
                "toc_count": len(scraped_data.get("toc", []) or []),
                "content_item_count": len(scraped_data.get("content_items", []) or []),
                "front_section_count": len(scraped_data.get("front_sections", []) or []),
                "back_section_count": len(scraped_data.get("back_sections", []) or []),
                **generated_files,
            }
            successes.append(result)
            for structure in structures:
                structure_counts[structure] += 1
                if len(examples_by_structure[structure]) < 5:
                    examples_by_structure[structure].append(
                        {
                            "title": result["title"],
                            "source_url": result["source_url"],
                        }
                    )
        except Exception as exc:
            failures.append(
                {
                    "index": index,
                    "source_url": entry.source_url,
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=20),
                }
            )

    summary = {
        "requested_successes": DESIRED_SUCCESS_COUNT,
        "attempted": min(len(entries), len(successes) + len(failures)),
        "successful_exports": len(successes),
        "failed_exports": len(failures),
        "structure_counts": dict(sorted(structure_counts.items())),
        "structure_examples": dict(examples_by_structure),
        "elapsed_seconds": round(time.time() - started_at, 2),
    }

    (REPORT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORT_DIR / "successes.json").write_text(
        json.dumps(successes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (REPORT_DIR / "failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False), flush=True)

    if len(successes) < DESIRED_SUCCESS_COUNT:
        raise RuntimeError(
            f"only {len(successes)} books completed end-to-end; see {REPORT_DIR / 'failures.json'}"
        )


if __name__ == "__main__":
    main()
