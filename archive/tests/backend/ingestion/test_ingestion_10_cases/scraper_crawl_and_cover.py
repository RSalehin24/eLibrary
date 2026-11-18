import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pytest
import requests
from django.db import IntegrityError
from django.utils import timezone

from apps.access.models import PreviewAccessSession
from apps.accounts.models import User
from apps.catalog.models import Book, BookContributor, BookSource, Category, Contributor, GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType, Series
from apps.common.models import LifecycleState, ReviewState
from apps.ingestion.models import (
    CatalogAutomationFrequency,
    BookSubmission,
    CatalogCurationRun,
    DuplicateReview,
    DuplicateReviewStatus,
    JobStatus,
    MatchCandidate,
    ProcessingJob,
    ResolutionStatus,
    SourceCatalogEntry,
    SourceCatalogRefreshState,
    SourceCatalogRefreshStatus,
    SubmissionOrigin,
    SubmissionStatus,
    TitleResolutionAttempt,
)
from apps.ingestion.services.curation import (
    get_catalog_automation_settings,
    next_catalog_automation_run_at,
    run_due_catalog_automation,
    source_catalog_entry_snapshots,
)
from apps.ingestion.pipeline import scraper as legacy_scraper
from apps.ingestion.services.legacy_adapter import normalize_text
from apps.ingestion.services.legacy_adapter import normalize_source_url
from apps.ingestion.services.normalization import (
    clean_extracted_dedication_html,
    extract_main_content_segments,
    extract_front_matter_entries,
    normalize_scraped_book,
    promote_leading_front_matter,
    split_leading_front_sections,
)
from apps.ingestion.services.resolution import CATALOG_URL, TitleResolver, get_with_host_fallback
from apps.ingestion.services.curation import (
    dispatch_catalog_curation_run,
    dispatch_source_catalog_refresh,
)
from apps.ingestion.services.submissions import (
    MAX_PROCESSING_JOB_ATTEMPTS,
    create_submission_records,
    detect_metadata_duplicate,
    dispatch_processing_job,
    find_exact_existing_book,
    process_submission_job,
    queue_submission,
    recover_stale_processing_jobs,
    sync_assets,
)
from apps.ingestion.services.curation_support.source_refresh import (
    process_source_catalog_refresh,
)
from apps.ingestion.tasks import process_submission_task
from apps.catalog.services import find_existing_book_by_source_url


def test_scrape_book_data_recurses_through_nested_toc_links(monkeypatch, tmp_path):
    root_url = "https://www.example.com/books/root-book/"
    child_url = "https://www.example.com/books/child-book/"
    lesson_url = "https://www.example.com/books/child-book/chapter-1/"

    html_map = {
        root_url: """
        <html>
          <head><title>মূল বই – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content">
              <p>মূল বইয়ের ভূমিকা</p>
              <p><strong>সূচীপত্র</strong></p>
              <ul>
                <li><a href="https://www.example.com/books/child-book/">সংগ্রহ খণ্ড</a></li>
              </ul>
            </div>
          </body>
        </html>
        """,
        child_url: """
        <html>
          <head><title>সংগ্রহ খণ্ড – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content">
              <p>খণ্ড পরিচিতি</p>
            </div>
          </body>
        </html>
        """,
        lesson_url: """
        <html>
          <head><title>অধ্যায় ১ – লেখক</title></head>
          <body>
            <div class="ld-tab-content ld-visible entry-content">
              <h2>অধ্যায় ১</h2>
              <p>পাতার ভেতরের লেখা</p>
            </div>
          </body>
        </html>
        """,
    }

    monkeypatch.setattr(
        legacy_scraper,
        "get_soup",
        lambda url, max_retries=3: legacy_scraper.BeautifulSoup(
            html_map[url], "html.parser"
        ),
    )
    monkeypatch.setattr(
        legacy_scraper,
        "create_output_folder",
        lambda _title: str(tmp_path / "output"),
    )
    monkeypatch.setattr(legacy_scraper, "download_cover_image", lambda *_args: None)

    def fake_scrape_all_lessons(url, **_options):
        if url == child_url:
            return [
                {
                    "title": "অধ্যায় ১",
                    "url": lesson_url,
                    "topics": [],
                    "has_topics": False,
                }
            ]
        return []

    monkeypatch.setattr(legacy_scraper, "scrape_all_lessons", fake_scrape_all_lessons)

    scraped = legacy_scraper.scrape_book_data(root_url)

    # When the source provides explicit body structure (TOC + content_items),
    # the landing page's leading prose is treated as pure front-matter and
    # promoted into ``front_sections`` rather than left inside main_content.
    front_section_blobs = "".join(
        section.get("html", "") for section in scraped.get("front_sections") or []
    )
    import unicodedata
    combined = unicodedata.normalize(
        "NFC", front_section_blobs + (scraped["main_content"] or "")
    )
    assert unicodedata.normalize("NFC", "মূল বইয়ের ভূমিকা") in combined
    assert "সূচীপত্র" not in scraped["main_content"]
    assert [entry["title"] for entry in scraped["toc"]] == ["সংগ্রহ খণ্ড"]
    assert [child["title"] for child in scraped["toc"][0]["children"]] == ["অধ্যায় ১"]
    assert [item["title"] for item in scraped["content_items"]] == [
        "সংগ্রহ খণ্ড",
        "অধ্যায় ১",
    ]
    assert scraped["content_items"][0]["path"] == ["সংগ্রহ খণ্ড"]
    assert scraped["content_items"][1]["path"] == ["সংগ্রহ খণ্ড", "অধ্যায় ১"]
    assert "খণ্ড পরিচিতি" in scraped["content_items"][0]["content"]
    assert "পাতার ভেতরের লেখা" in scraped["content_items"][1]["content"]


def test_download_cover_image_uses_retry_session_and_saves_the_cover(monkeypatch, tmp_path):
    class FakeResponse:
        status_code = 200
        content = b"cover-bytes"

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url, headers=None, timeout=None):
            self.calls.append(
                {
                    "url": url,
                    "headers": headers,
                    "timeout": timeout,
                }
            )
            return FakeResponse()

    session = FakeSession()
    monkeypatch.setattr(
        legacy_scraper,
        "create_session_with_retries",
        lambda: session,
    )

    soup = legacy_scraper.BeautifulSoup(
        """
        <figure class="entry-image-link entry-image-single">
          <img src="https://cdn.example.com/cover.webp" />
        </figure>
        """,
        "html.parser",
    )

    filename = legacy_scraper.download_cover_image(soup, str(tmp_path))

    assert filename == "book_cover.webp"
    assert session.calls == [
        {
            "url": "https://cdn.example.com/cover.webp",
            "headers": legacy_scraper.HEADERS,
            "timeout": 30,
        }
    ]
    assert (tmp_path / filename).read_bytes() == b"cover-bytes"


def test_scrape_all_lessons_waits_between_pages(monkeypatch):
    seen_urls = []
    sleep_calls = []
    lesson_pages = {
        "https://www.example.com/books/example/?ld-courseinfo-lesson-page=1": {
            "lessons": [{"title": "প্রথম পাঠ", "url": "lesson-1", "topics": [], "has_topics": False}],
            "total_pages": 2,
        },
        "https://www.example.com/books/example/?ld-courseinfo-lesson-page=2": {
            "lessons": [{"title": "দ্বিতীয় পাঠ", "url": "lesson-2", "topics": [], "has_topics": False}],
            "total_pages": 2,
        },
    }

    def fake_get_soup(url):
        seen_urls.append(url)
        return url

    monkeypatch.setattr(legacy_scraper, "get_soup", fake_get_soup)
    monkeypatch.setattr(
        legacy_scraper,
        "scrape_lesson_list",
        lambda soup: lesson_pages[soup]["lessons"],
    )
    monkeypatch.setattr(
        legacy_scraper,
        "get_total_pages",
        lambda soup: lesson_pages[soup]["total_pages"],
    )
    monkeypatch.setattr(legacy_scraper.time, "sleep", sleep_calls.append)

    lessons = legacy_scraper.scrape_all_lessons(
        "https://www.example.com/books/example/",
    )

    assert [lesson["title"] for lesson in lessons] == ["প্রথম পাঠ", "দ্বিতীয় পাঠ"]
    assert seen_urls == [
        "https://www.example.com/books/example/?ld-courseinfo-lesson-page=1",
        "https://www.example.com/books/example/?ld-courseinfo-lesson-page=2",
    ]
    assert sleep_calls == [1]
