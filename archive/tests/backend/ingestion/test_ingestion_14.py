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
def test_process_submission_job_does_not_reuse_same_title_book_when_source_url_differs(
    tmp_path,
    monkeypatch,
):
    user = User.objects.create_user(email="unique-title-only@example.com", password="strong-password-123")
    existing_source_url = "https://www.example.com/books/shared-title-old/"
    incoming_source_url = "https://www.example.com/books/shared-title-new/"

    existing_book = Book.objects.create(
        title="শ্রেষ্ঠ কবিতা",
        source_site="example.com",
        state="ready",
        review_state="approved",
    )
    BookSource.objects.create(
        book=existing_book,
        source_url=existing_source_url,
        normalized_source_url=normalize_source_url(existing_source_url),
        source_title=existing_book.title,
    )

    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input=incoming_source_url,
        normalized_input=normalize_text(incoming_source_url),
        resolved_url=incoming_source_url,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_confidence=1.0,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(submission=submission)

    sample = {
        "book_title": "শ্রেষ্ঠ কবিতা",
        "author": "কবি দুই",
        "book_type": "গল্প",
        "series": "",
        "cover": "book_cover.jpg",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "",
        "dedication": "",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [
            {
                "title": "অধ্যায় ১",
                "content": "<p>বিষয়বস্তু</p>",
                "type": "lesson",
                "parent": None,
            }
        ],
        "output_folder": str(tmp_path),
    }

    monkeypatch.setattr("apps.ingestion.services.submissions.capture_source_page_metadata", lambda _url: None)
    monkeypatch.setattr("apps.ingestion.services.submissions.scrape_book", lambda _url: sample)

    original_create = Book.objects.create
    conflict_raised = {"value": False}

    def flaky_create(*args, **kwargs):
        if not conflict_raised["value"] and kwargs.get("title") == "শ্রেষ্ঠ কবিতা":
            conflict_raised["value"] = True
            raise IntegrityError(
                'duplicate key value violates unique constraint "uniq_book_source_normalized_title"'
            )
        return original_create(*args, **kwargs)

    monkeypatch.setattr(Book.objects, "create", flaky_create)

    with pytest.raises(IntegrityError, match="uniq_book_source_normalized_title"):
        process_submission_job(str(job.id))

    job.refresh_from_db()
    submission.refresh_from_db()
    assert conflict_raised["value"] is True
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 1
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.linked_book_id is None


@pytest.mark.django_db
def test_find_exact_existing_book_does_not_match_when_categories_differ():
    existing_book = Book.objects.create(
        title="শ্রেষ্ঠ কবিতা",
        source_site="example.com",
        state="ready",
        review_state="approved",
    )
    existing_author = Contributor.objects.create(name="মহাদেব সাহ")
    existing_category = Category.objects.create(name="কবিতা")
    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")
    book_category = existing_book.book_categories.model
    book_category.objects.create(book=existing_book, category=existing_category, raw_value=existing_category.name)

    matched = find_exact_existing_book(
        {
            "book_title": "শ্রেষ্ঠ কবিতা",
            "author": "মহাদেব সাহ",
            "book_type": "গল্প",
        }
    )

    assert matched is None


@pytest.mark.django_db
def test_detect_metadata_duplicate_does_not_match_when_categories_differ():
    existing_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready", review_state="approved")
    existing_author = Contributor.objects.create(name="মহাদেব সাহ")
    existing_category = Category.objects.create(name="কবিতা")
    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")
    book_category = existing_book.book_categories.model
    book_category.objects.create(book=existing_book, category=existing_category, raw_value=existing_category.name)

    duplicate = detect_metadata_duplicate(
        {
            "book_title": "শ্রেষ্ঠ কবিতা",
            "author": "মহাদেব সাহ",
            "book_type": "গল্প",
        }
    )

    assert duplicate is None


@pytest.mark.django_db
def test_detect_metadata_duplicate_does_not_match_when_target_series_does_not_match_existing():
    existing_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready", review_state="approved")
    existing_author = Contributor.objects.create(name="মহাদেব সাহ")
    existing_category = Category.objects.create(name="কবিতা")
    existing_series = Series.objects.create(name="প্রথম খণ্ড")

    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")
    existing_book.book_categories.model.objects.create(
        book=existing_book,
        category=existing_category,
        raw_value=existing_category.name,
    )
    existing_book.book_series.model.objects.create(
        book=existing_book,
        series=existing_series,
        raw_value=existing_series.name,
        sort_order=0,
    )

    duplicate = detect_metadata_duplicate(
        {
            "book_title": "শ্রেষ্ঠ কবিতা",
            "author": "মহাদেব সাহ",
            "book_type": "কবিতা",
            "series": "দ্বিতীয় খণ্ড",
        }
    )

    assert duplicate is None


@pytest.mark.django_db
def test_detect_metadata_duplicate_does_not_match_when_translators_differ():
    existing_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready", review_state="approved")
    existing_author = Contributor.objects.create(name="মহাদেব সাহ")
    existing_translator = Contributor.objects.create(name="অনুবাদক এক")
    existing_category = Category.objects.create(name="কবিতা")

    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")
    BookContributor.objects.create(book=existing_book, contributor=existing_translator, role="translator")
    existing_book.book_categories.model.objects.create(
        book=existing_book,
        category=existing_category,
        raw_value=existing_category.name,
    )

    duplicate = detect_metadata_duplicate(
        {
            "book_title": "শ্রেষ্ঠ কবিতা",
            "author": "মহাদেব সাহ",
            "book_type": "কবিতা",
            "book_info": "<p>অনুবাদক: অনুবাদক দুই</p>",
        }
    )

    assert duplicate is None
