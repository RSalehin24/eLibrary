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
from apps.ingestion.services.submissions import (
    create_submission_records,
    detect_metadata_duplicate,
    find_exact_existing_book,
    process_submission_job,
    queue_submission,
    sync_assets,
)
from apps.ingestion.tasks import process_submission_task
from apps.catalog.services import find_existing_book_by_source_url


def test_extract_main_content_segments_omits_dedication_heading_from_extracted_dedication():
    _, dedication_html, cleaned_main_content = extract_main_content_segments(
        """
        <div>
          <p>উৎসর্গ</p>
          <p><strong>উৎসর্গ</strong></p>
          <p>আহমেদ নাফিস শাহরিয়ারকে</p>
          <p>২২ আগস্ট, ১৯৯৪</p>
          <p><strong>ভূমিকা</strong></p>
          <p>এটাই মূল কনটেন্ট।</p>
        </div>
        """
    )

    assert "আহমেদ নাফিস শাহরিয়ারকে" in dedication_html
    assert "উৎসর্গ" not in dedication_html
    assert "এটাই মূল কনটেন্ট।" in cleaned_main_content


def test_extract_main_content_segments_stops_dedication_before_strong_only_title():
    _, dedication_html, cleaned_main_content = extract_main_content_segments(
        """
        <div>
          <p>উৎসর্গ</p>
          <p>শ্রীযুক্ত সত্যেন্দ্রনাথ ঠাকুর</p>
          <p>দাদা মহাশয়</p>
          <p><strong>কবির মন্তব্য</strong></p>
          <p>এই অংশ আর উৎসর্গ নয়।</p>
        </div>
        """
    )

    assert "শ্রীযুক্ত সত্যেন্দ্রনাথ ঠাকুর" in dedication_html
    assert "দাদা মহাশয়" in dedication_html
    assert "কবির মন্তব্য" not in dedication_html
    assert "কবির মন্তব্য" in cleaned_main_content
    assert "এই অংশ আর উৎসর্গ নয়।" in cleaned_main_content


def test_split_leading_front_sections_uses_multiline_strong_title_as_single_section_heading():
    sections, cleaned_main_content = split_leading_front_sections(
        """
        <div>
          <p><strong>২০০১ : আ স্পেস ওডিসি – আর্থার সি ক্লার্ক<br/>ভাষান্তর : মাকসুদুজ্জামান খান</strong><strong> </strong><strong></strong></p>
          <p>প্রারম্ভিক মন্তব্য।</p>
          <p><strong>সূচীপত্র</strong></p>
          <ul><li>অধ্যায় ১</li></ul>
        </div>
        """
    )

    assert sections == [
        {
            "title": "২০০১ : আ স্পেস ওডিসি – আর্থার সি ক্লার্ক\nভাষান্তর : মাকসুদুজ্জামান খান",
            "html": "<p>প্রারম্ভিক মন্তব্য।</p>",
        }
    ]
    assert "সূচীপত্র" not in cleaned_main_content
    assert "অধ্যায় ১" not in cleaned_main_content
    assert "প্রারম্ভিক মন্তব্য।" not in cleaned_main_content


def test_inline_toc_extraction_builds_toc_and_content_from_main_content():
    toc, content_items, cleaned_main_content = legacy_scraper.extract_inline_toc_and_content(
        """
        <div class="ld-tab-content ld-visible entry-content">
          <h2>উপন্যাস সমগ্র – রবীন্দ্রনাথ ঠাকুর</h2>
          <p><strong>সূচীপত্র</strong></p>
          <ul>
            <li><a href="#section-one">প্রথম অংশ</a></li>
            <li><a href="#section-two">দ্বিতীয় অংশ</a></li>
          </ul>
          <h3 id="section-one">প্রথম অংশ</h3>
          <p>প্রথম অংশের লেখা</p>
          <h3 id="section-two">দ্বিতীয় অংশ</h3>
          <p>দ্বিতীয় অংশের লেখা</p>
        </div>
        """
    )

    assert [entry["title"] for entry in toc] == ["প্রথম অংশ", "দ্বিতীয় অংশ"]
    assert [item["title"] for item in content_items] == ["প্রথম অংশ", "দ্বিতীয় অংশ"]
    assert "প্রথম অংশের লেখা" in content_items[0]["content"]
    assert "দ্বিতীয় অংশের লেখা" in content_items[1]["content"]
    assert "সূচীপত্র" not in cleaned_main_content
    assert "উপন্যাস সমগ্র – রবীন্দ্রনাথ ঠাকুর" in cleaned_main_content
    assert "প্রথম অংশের লেখা" not in cleaned_main_content


def test_inline_toc_extraction_removes_embedded_toc_even_without_section_bodies():
    toc, content_items, cleaned_main_content = legacy_scraper.extract_inline_toc_and_content(
        """
        <div class="ld-tab-content ld-visible entry-content">
          <h2>উপন্যাস সমগ্র – রবীন্দ্রনাথ ঠাকুর</h2>
          <p>উপন্যাস সমগ্র – রবীন্দ্রনাথ ঠাকুর</p>
          <p><strong>সূচীপত্র</strong></p>
          <ul>
            <li><a href="https://www.example.com/books/dui-bon/">দুই বোন – রবীন্দ্রনাথ ঠাকুর</a></li>
            <li><a href="https://www.example.com/books/chokher-bali/">চোখের বালি – রবীন্দ্রনাথ ঠাকুর</a></li>
          </ul>
        </div>
        """
    )

    assert [entry["title"] for entry in toc] == [
        "দুই বোন – রবীন্দ্রনাথ ঠাকুর",
        "চোখের বালি – রবীন্দ্রনাথ ঠাকুর",
    ]
    assert content_items == []
    assert "সূচীপত্র" not in cleaned_main_content
    assert "দুই বোন – রবীন্দ্রনাথ ঠাকুর" not in cleaned_main_content
    assert "উপন্যাস সমগ্র – রবীন্দ্রনাথ ঠাকুর" in cleaned_main_content


def test_inline_toc_extraction_handles_paragraph_style_lesson_links():
    """দুর্গরহস্য-style books: TOC heading is 'সূচী ॥' with <p><a> links (not <ul>/<ol>)."""
    toc, content_items, cleaned_main_content = legacy_scraper.extract_inline_toc_and_content(
        """
        <div class="entry-content">
          <p>দুর্গরহস্য। বাক-সাহিত্য। তৃতীয় প্রকাশ, চৈত্র ১৩৭১।</p>
          <p>সূচী ॥</p>
          <p><a href="https://www.example.com/lessons/chitrachor/">চিত্রচোর</a></p>
          <p><a href="https://www.example.com/lessons/durgahasya/">দুর্গরহস্য</a></p>
        </div>
        """
    )

    assert [entry["title"] for entry in toc] == ["চিত্রচোর", "দুর্গরহস্য"]
    assert all(entry["url"] for entry in toc)
    assert content_items == []
    assert "সূচী" not in cleaned_main_content
    assert "চিত্রচোর" not in cleaned_main_content
    # The lesson link paragraphs are removed, but the book title paragraph stays
    assert "/lessons/chitrachor/" not in cleaned_main_content
    assert "/lessons/durgahasya/" not in cleaned_main_content
