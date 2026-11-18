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
def test_find_exact_existing_book_requires_author_overlap_for_same_title():
    existing_book = Book.objects.create(
        title="শ্রেষ্ঠ কবিতা",
        source_site="example.com",
        state="ready",
        review_state="approved",
    )
    existing_author = Contributor.objects.create(name="কবি এক")
    existing_category = Category.objects.create(name="কবিতা")
    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")
    existing_book.book_categories.model.objects.create(
        book=existing_book,
        category=existing_category,
        raw_value=existing_category.name,
    )

    matched = find_exact_existing_book(
        {"book_title": "শ্রেষ্ঠ কবিতা", "author": "কবি দুই", "book_type": "কবিতা"}
    )
    assert matched is None

    matched_same_author = find_exact_existing_book(
        {"book_title": "শ্রেষ্ঠ কবিতা", "author": "কবি এক", "book_type": "কবিতা"}
    )
    assert matched_same_author is not None
    assert matched_same_author.id == existing_book.id


@pytest.mark.django_db
def test_process_submission_job_recovers_when_book_create_hits_source_title_unique_conflict(
    tmp_path,
    monkeypatch,
):
    user = User.objects.create_user(email="unique-conflict@example.com", password="strong-password-123")
    source_url = "https://www.example.com/books/unique-conflict-book/"
    existing_book = Book.objects.create(
        title="শ্রেষ্ঠ কবিতা",
        source_site="example.com",
        state="ready",
        review_state="approved",
    )
    existing_author = Contributor.objects.create(name="কবি এক")
    existing_category = Category.objects.create(name="কবিতা")
    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")
    existing_book.book_categories.model.objects.create(
        book=existing_book,
        category=existing_category,
        raw_value=existing_category.name,
    )
    lookup_calls = {"count": 0}
    normalized_source_url = normalize_source_url(source_url)

    def staged_source_url_lookup(normalized_url):
        lookup_calls["count"] += 1
        if lookup_calls["count"] == 1:
            return None
        if normalized_url == normalized_source_url:
            return existing_book
        return None

    monkeypatch.setattr("apps.ingestion.services.submissions.find_existing_book_by_source_url", staged_source_url_lookup)

    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input=source_url,
        normalized_input=normalize_text(source_url),
        resolved_url=source_url,
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

    def fake_generate_exports(book_data):
        output_dir = Path(book_data["output_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text("<html><body>book</body></html>", encoding="utf-8")
        (output_dir / "শ্রেষ্ঠ কবিতা.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr("apps.ingestion.services.submissions.generate_exports", fake_generate_exports)

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

    process_submission_job(str(job.id))
    submission.refresh_from_db()

    assert conflict_raised["value"] is True
    assert lookup_calls["count"] >= 2
    assert submission.status == SubmissionStatus.READY
    assert submission.linked_book_id == existing_book.id
