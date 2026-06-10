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
from apps.common.source_site_semantic_audit import audit_scraped_book
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.services.normalization import (
    BLOCK_TAG_NAMES,
    block_heading_candidate_text,
    combined_front_matter_html,
    extract_front_matter_entries,
    infer_numeric_structured_content_from_main_content,
    is_probable_source_navigation_section,
    normalize_scraped_book,
)
from apps.processing import source as processing_source


DESIRED_SUCCESS_COUNT = int(os.environ.get("SOURCE_SITE_DESIRED_SUCCESS_COUNT", "200") or 200)
CANDIDATE_LIMIT = int(os.environ.get("SOURCE_SITE_CANDIDATE_LIMIT", "260") or 260)
ARCHIVE_REFRESH_PAGES = int(os.environ.get("SOURCE_SITE_REFRESH_PAGES", "25") or 25)
REPORT_DIR = Path("/app/storage/semantic-validation-report")
EXPORT_ROOT = Path("/app/storage/semantic-validation")
SOURCE_URLS_PATH = Path("/app/storage/live-validation-report/successes.json")
PRIORITY_SOURCE_URLS = [
    "https://www.example.com/books/example-book/",
]
USE_SAVED_SOURCE_URLS = (
    os.environ.get("SOURCE_SITE_USE_SAVED_SOURCE_URLS", "").strip().lower()
    in {"1", "true", "yes", "on"}
)


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


def normalized_signature(text):
    cleaned = plain_text_from_html(text) if "<" in str(text or "") else str(text or "")
    cleaned = " ".join(cleaned.split())
    return cleaned.casefold()


def duplicate_html_block_signatures(html):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    duplicates = []
    for block in soup.find_all(BLOCK_TAG_NAMES):
        text = block.get_text(" ", strip=True)
        signature = normalized_signature(text)
        if len(signature) < 8:
            continue
        if signature in seen:
            duplicates.append(text)
            continue
        seen.add(signature)
    return duplicates


def duplicate_section_titles(sections):
    seen = set()
    duplicates = []
    for section in sections or []:
        signature = (
            normalized_signature(section.get("title", "")),
            normalized_signature(section.get("html", "")),
        )
        if not signature[0] or not signature[1]:
            continue
        if signature in seen:
            duplicates.append(section.get("title", ""))
            continue
        seen.add(signature)
    return duplicates


def has_underlined_toc_hover(html_text):
    return (
        "toc-topic a:hover{color:#2980b9;text-decoration:underline;}" in html_text
        or "toc-standalone a:hover{color:#3498db;text-decoration:underline;}" in html_text
    )


def possible_main_content_headings(main_content_html):
    if not main_content_html:
        return []
    soup = BeautifulSoup(main_content_html, "html.parser")
    headings = []
    for block in soup.find_all(BLOCK_TAG_NAMES):
        title = block_heading_candidate_text(block)
        if title:
            headings.append(title)
    return headings


def suspicious_contributor_names(contributors):
    suspicious = []
    for contributor in contributors or []:
        name = str(contributor.get("name") or "").strip()
        signature = normalized_signature(name)
        if not signature:
            continue
        if signature in {"মো", "মোঃ", "মো:"}:
            suspicious.append(name)
            continue
        if any(helper in signature.split() for helper in ("করেছেন", "কর্তৃক", "সম্পাদনা", "অনুবাদ")):
            suspicious.append(name)
    return suspicious


def duplicate_front_matter_entries(scraped_data):
    combined_html = combined_front_matter_html(
        scraped_data.get("book_info", ""),
        scraped_data.get("main_content", ""),
    )
    seen = set()
    duplicates = []
    for entry in extract_front_matter_entries(combined_html):
        signature = (
            normalized_signature(entry.get("key", "")),
            normalized_signature(entry.get("value", "")),
        )
        if signature in seen:
            duplicates.append(entry)
            continue
        seen.add(signature)
    return duplicates


def export_issue_keys(export_dir, scraped_data):
    issues = []
    html_path = export_dir / "book.html"
    html_text = html_path.read_text(encoding="utf-8")
    front_sections = scraped_data.get("front_sections", []) or []
    back_sections = scraped_data.get("back_sections", []) or []

    if duplicate_html_block_signatures(scraped_data.get("book_info", "")):
        issues.append("duplicate_book_info_blocks")
    if duplicate_html_block_signatures(scraped_data.get("dedication", "")):
        issues.append("duplicate_dedication_blocks")
    if duplicate_section_titles(front_sections):
        issues.append("duplicate_front_sections")
    if duplicate_section_titles(back_sections):
        issues.append("duplicate_back_sections")
    if any(
        is_probable_source_navigation_section(section.get("title", ""), section.get("html", ""))
        for section in [*front_sections, *back_sections]
    ):
        issues.append("source_navigation_sections")
    if has_underlined_toc_hover(html_text):
        issues.append("html_toc_underlined_links")
    if (
        not scraped_data.get("toc")
        and not scraped_data.get("content_items")
        and (
            len(possible_main_content_headings(scraped_data.get("main_content", ""))) >= 2
            or infer_numeric_structured_content_from_main_content(
                scraped_data.get("main_content", ""),
            )[1]
        )
    ):
        issues.append("unsplit_single_flow_book")
    if duplicate_front_matter_entries(scraped_data):
        issues.append("duplicate_detail_front_matter_entries")

    normalized = normalize_scraped_book(scraped_data)
    if suspicious_contributor_names(normalized.get("contributors", [])):
        issues.append("suspicious_contributor_names")

    epub_files = sorted(export_dir.glob("*.epub"))
    if epub_files:
        with zipfile.ZipFile(epub_files[0]) as archive:
            nav_text = archive.read("EPUB/nav.xhtml").decode("utf-8", errors="ignore")
            toc_href = 'href="toc.xhtml"'
            lesson_match = re.search(r'href="lesson_\d+\.xhtml"', nav_text)
            if scraped_data.get("toc") and toc_href not in nav_text:
                issues.append("epub_missing_visible_toc")
            if toc_href in nav_text and lesson_match and nav_text.index(toc_href) > lesson_match.start():
                issues.append("epub_toc_after_content")

    return issues


def fetch_candidate_urls(limit):
    if USE_SAVED_SOURCE_URLS and SOURCE_URLS_PATH.exists():
        rows = json.loads(SOURCE_URLS_PATH.read_text(encoding="utf-8"))
        urls = [row["source_url"] for row in rows if row.get("source_url")]
        if urls:
            unique_urls = []
            seen = set()
            for url in [*PRIORITY_SOURCE_URLS, *urls]:
                if not url or url in seen:
                    continue
                seen.add(url)
                unique_urls.append(url)
            return unique_urls[:limit]

    queryset = (
        SourceCatalogEntry.objects.filter(source_url__contains="/books/")
        .order_by("id")
        .values_list("source_url", flat=True)
    )
    unique_urls = []
    seen = set()
    for url in [*PRIORITY_SOURCE_URLS, *list(queryset[:limit])]:
        if not url or url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
    return unique_urls[:limit]


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


def main():
    started_at = time.time()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)

    print(
        json.dumps(
            {"stage": "refresh_archive", "max_pages": ARCHIVE_REFRESH_PAGES},
            ensure_ascii=False,
        ),
        flush=True,
    )
    refresh_source_archive(max_pages=ARCHIVE_REFRESH_PAGES)

    urls = fetch_candidate_urls(CANDIDATE_LIMIT)
    if len(urls) < DESIRED_SUCCESS_COUNT:
        raise RuntimeError(
            f"expected at least {DESIRED_SUCCESS_COUNT} source URLs after refresh, got {len(urls)}"
        )

    successes = []
    failures = []
    issue_counts = Counter()
    structure_counts = Counter()
    examples_by_issue = defaultdict(list)

    for index, source_url in enumerate(urls, start=1):
        if len(successes) >= DESIRED_SUCCESS_COUNT:
            break

        print(
            json.dumps(
                {
                    "stage": "semantic_audit",
                    "candidate_index": index,
                    "successes": len(successes),
                    "url": source_url,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

        try:
            scraped_data = processing_source.scrape_book_high_fidelity(source_url)
            if not isinstance(scraped_data, dict):
                raise AssertionError("scrape returned no structured payload")

            export_dir = ensure_export_dir(index, scraped_data.get("book_title", ""))
            copy_cover_if_present(scraped_data, export_dir)
            scraped_data["output_folder"] = str(export_dir)
            processing_source.generate_exports(scraped_data)
            generated_files = validate_generated_files(export_dir, scraped_data)

            audit = audit_scraped_book(scraped_data)
            structures = classify_structure(scraped_data)
            for structure in structures:
                structure_counts[structure] += 1

            issue_names = []
            extra_issue_keys = export_issue_keys(export_dir, scraped_data)
            for extra_issue_key in extra_issue_keys:
                issue_counts[extra_issue_key] += 1
                issue_names.append(extra_issue_key)
                if len(examples_by_issue[extra_issue_key]) < 10:
                    examples_by_issue[extra_issue_key].append(
                        {
                            "title": scraped_data.get("book_title", ""),
                            "source_url": source_url,
                        }
                    )

            for issue_key in (
                "missing_contributors",
                "unsupported_contributors",
                "dead_toc_paths",
                "missing_toc_paths_for_content",
                "duplicate_toc_paths",
                "duplicate_content_paths",
            ):
                if audit.get(issue_key):
                    issue_counts[issue_key] += 1
                    issue_names.append(issue_key)
                    if len(examples_by_issue[issue_key]) < 10:
                        examples_by_issue[issue_key].append(
                            {
                                "title": scraped_data.get("book_title", ""),
                                "source_url": source_url,
                            }
                        )

            result = {
                "index": index,
                "source_url": source_url,
                "title": scraped_data.get("book_title", ""),
                "author_line": scraped_data.get("author", ""),
                "structures": structures,
                "issue_keys": issue_names,
                **generated_files,
                **audit,
            }

            if audit["has_deltas"]:
                failures.append(result)
            else:
                successes.append(result)
        except Exception as exc:
            issue_counts["execution_failures"] += 1
            failures.append(
                {
                    "index": index,
                    "source_url": source_url,
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=20),
                }
            )

    summary = {
        "requested_clean_books": DESIRED_SUCCESS_COUNT,
        "attempted": min(len(urls), len(successes) + len(failures)),
        "clean_books": len(successes),
        "books_with_deltas": len(failures),
        "used_saved_source_urls": USE_SAVED_SOURCE_URLS,
        "issue_counts": dict(sorted(issue_counts.items())),
        "issue_examples": dict(examples_by_issue),
        "structure_counts": dict(sorted(structure_counts.items())),
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


if __name__ == "__main__":
    main()
