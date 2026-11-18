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


@pytest.mark.django_db
def test_next_catalog_automation_run_at_uses_monthly_frequency_from_latest_run():
    timezone_value = timezone.get_current_timezone()
    now = timezone.make_aware(datetime(2026, 3, 23, 10, 0, 0), timezone_value)
    settings_obj = get_catalog_automation_settings()
    settings_obj.enabled = True
    settings_obj.daily_run_time = now.astimezone(timezone_value).replace(hour=6, minute=30).time()
    settings_obj.frequency = CatalogAutomationFrequency.MONTHLY
    settings_obj.save()
    type(settings_obj).objects.filter(pk=settings_obj.pk).update(updated_at=now - timedelta(days=90))
    settings_obj.refresh_from_db()

    latest_run = CatalogCurationRun.objects.create(
        trigger="scheduled",
        mode="pending",
        status="succeeded",
        refresh_catalog=True,
        refresh_max_pages=10,
    )
    CatalogCurationRun.objects.filter(pk=latest_run.pk).update(
        created_at=timezone.make_aware(datetime(2026, 1, 31, 6, 30, 0), timezone_value)
    )
    latest_run.refresh_from_db()

    next_run_at = next_catalog_automation_run_at(settings_obj, now=now)

    assert timezone.localtime(next_run_at).month == 2
    assert timezone.localtime(next_run_at).day in {28, 29}


def test_front_matter_extraction_handles_inline_labels_and_role_detection():
    book_info_html = """
    <p><strong>অনুবাদ</strong>: অনুবাদক এক, অনুবাদক দুই</p>
    <p><strong>প্রথম প্রকাশ</strong>: জানুয়ারি ২০০১</p>
    <p><strong>প্রকাশক</strong> : প্রকাশনী</p>
    """

    entries = extract_front_matter_entries(book_info_html)
    normalized = normalize_scraped_book(
        {
            "book_title": "উদাহরণ",
            "author": "লেখক এক",
            "series": "",
            "book_type": "",
            "book_info": book_info_html,
        }
    )

    assert [entry["key"] for entry in entries] == ["translator", "first_published", "publisher"]
    assert any(
        contributor["name"] == "অনুবাদক এক" and contributor["role"] == "translator"
        for contributor in normalized["contributors"]
    )
    assert any(
        contributor["name"] == "অনুবাদক দুই" and contributor["role"] == "translator"
        for contributor in normalized["contributors"]
    )
    assert any(
        contributor["name"] == "প্রকাশনী" and contributor["role"] == "publisher"
        for contributor in normalized["contributors"]
    )


def test_front_matter_promotion_extracts_title_prefixed_translator_and_publication_from_main_content():
    main_content_html = """
    <div>
      <h2 class="wp-block-heading">ম্যালিস – কিয়েগো হিগাশিনো</h2>
      <p><strong>ম্যালিস – কিয়েগো হিগাশিনো</strong><br/>অনুবাদ: সালমান হক, ইশরাক অর্ণব</p>
      <p>প্রথম প্রকাশ: মার্চ ২০২৩</p>
      <p><strong>ভূমিকা</strong></p>
      <p>এটাই মূল কনটেন্ট।</p>
    </div>
    """

    book_info_html, cleaned_main_content = promote_leading_front_matter("", main_content_html)
    entries = extract_front_matter_entries(book_info_html)
    normalized = normalize_scraped_book(
        {
            "book_title": "ম্যালিস",
            "author": "কেইগো হিগাশিনো",
            "series": "",
            "book_type": "",
            "book_info": "",
            "main_content": main_content_html,
        }
    )

    assert any(entry["role"] == "translator" and "সালমান হক" in entry["value"] for entry in entries)
    assert any(entry["key"] == "first_published" and entry["value"] == "মার্চ ২০২৩" for entry in entries)
    assert "অনুবাদ: সালমান হক, ইশরাক অর্ণব" not in cleaned_main_content
    assert "প্রথম প্রকাশ: মার্চ ২০২৩" not in cleaned_main_content
    assert "এটাই মূল কনটেন্ট।" in cleaned_main_content
    assert any(
        contributor["name"] == "সালমান হক" and contributor["role"] == "translator"
        for contributor in normalized["contributors"]
    )
    assert any(
        contributor["name"] == "ইশরাক অর্ণব" and contributor["role"] == "translator"
        for contributor in normalized["contributors"]
    )


def test_normalize_scraped_book_ignores_translator_biography_and_keeps_only_name():
    normalized = normalize_scraped_book(
        {
            "book_title": "উদাহরণ",
            "author": "লেখক এক",
            "series": "",
            "book_type": "",
            "book_info": """
            <p><strong>অনুবাদক</strong>: মাকসুদুজ্জামান খান বায়োটেকনোলজি এন্ড জেনেটিক ইঞ্জিনিয়ারিং এ পড়ালেখা করছেন।
            তিনি আর্থার সি ক্লার্ক ও আইজাক আসিমভের বেশ কিছু লেখা ভাষান্তর করেছেন।, মাকসুদুজ্জামান খান</p>
            """,
        }
    )

    translators = [entry["name"] for entry in normalized["contributors"] if entry["role"] == "translator"]

    assert translators == ["মাকসুদুজ্জামান খান"]


def test_normalize_scraped_book_splits_multiple_translators_joined_with_connector():
    normalized = normalize_scraped_book(
        {
            "book_title": "উদাহরণ",
            "author": "লেখক এক",
            "series": "",
            "book_type": "",
            "book_info": """
            <p><strong>অনুবাদ</strong>: সালমান হক ও ইশরাক অর্ণব</p>
            """,
        }
    )

    translators = [entry["name"] for entry in normalized["contributors"] if entry["role"] == "translator"]

    assert translators == ["সালমান হক", "ইশরাক অর্ণব"]


def test_front_matter_extraction_rejects_translator_prose_without_name_like_values():
    book_info_html = """
    <p><strong>অনুবাদক</strong>: তিনি আর্থার সি ক্লার্ক ও আইজাক আসিমভের বেশ কিছু লেখা ভাষান্তর করেছেন।</p>
    """

    entries = extract_front_matter_entries(book_info_html)
    normalized = normalize_scraped_book(
        {
            "book_title": "উদাহরণ",
            "author": "লেখক এক",
            "series": "",
            "book_type": "",
            "book_info": book_info_html,
        }
    )

    assert not any(entry["role"] == "translator" for entry in entries)
    assert not any(contributor["role"] == "translator" for contributor in normalized["contributors"])


def test_clean_extracted_dedication_html_removes_repeated_dedication_heading():
    dedication_html = clean_extracted_dedication_html(
        """
        <p>উৎসর্গ</p>
        <p><strong>উৎসর্গ</strong></p>
        <p>আহমেদ নাফিস শাহরিয়ারকে</p>
        <p>২২ আগস্ট, ১৯৯৪</p>
        """
    )

    assert "আহমেদ নাফিস শাহরিয়ারকে" in dedication_html
    assert "২২ আগস্ট, ১৯৯৪" in dedication_html
    assert "উৎসর্গ" not in dedication_html


def test_clean_extracted_dedication_html_keeps_inline_content_after_label():
    dedication_html = clean_extracted_dedication_html(
        """
        <p>উৎসর্গ :<br/>পাঠক, আপনাকে…</p>
        """
    )

    assert "পাঠক, আপনাকে" in dedication_html
    assert "উৎসর্গ" not in dedication_html
