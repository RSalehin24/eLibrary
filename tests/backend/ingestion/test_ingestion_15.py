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
def test_find_exact_existing_book_does_not_match_when_translators_differ():
    existing_book = Book.objects.create(
        title="শ্রেষ্ঠ কবিতা",
        source_site="example.com",
        state="ready",
        review_state="approved",
    )
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

    matched = find_exact_existing_book(
        {
            "book_title": "শ্রেষ্ঠ কবিতা",
            "author": "মহাদেব সাহ",
            "book_type": "কবিতা",
            "book_info": "<p>অনুবাদক: অনুবাদক দুই</p>",
        }
    )

    assert matched is None


@pytest.mark.django_db
def test_title_submission_does_not_auto_fulfill_from_title_only_local_match(monkeypatch):
    user = User.objects.create_user(email="title-only-local@example.com", password="strong-password-123")
    existing_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready", review_state="approved")
    existing_author = Contributor.objects.create(name="অন্য কবি")
    BookContributor.objects.create(book=existing_book, contributor=existing_author, role="author")

    def fake_resolve_submission(submission, force_refresh=False):
        submission.resolution_status = ResolutionStatus.UNRESOLVED
        submission.status = SubmissionStatus.NEEDS_REVIEW
        submission.review_state = ReviewState.NEEDS_REVIEW
        submission.error_message = "No confident catalog match was found."
        submission.save(update_fields=["resolution_status", "status", "review_state", "error_message", "updated_at"])
        return submission

    monkeypatch.setattr("apps.ingestion.services.submissions.resolve_submission", fake_resolve_submission)

    submission = create_submission_records(
        submitter=user,
        parsed_entries=[{"kind": "title", "value": "শ্রেষ্ঠ কবিতা"}],
        auto_process=False,
    )[0]

    submission.refresh_from_db()
    assert submission.linked_book_id is None
    assert submission.status == SubmissionStatus.NEEDS_REVIEW
    assert submission.raw_payload.get("served_from_database") is None


@pytest.mark.django_db
def test_process_submission_job_handles_missing_cover_url_without_db_null_violation(tmp_path, monkeypatch):
    user = User.objects.create_user(email="cover-null@example.com", password="strong-password-123")
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/cover-null-book/",
        normalized_input="cover null book",
        resolved_url="https://www.example.com/books/cover-null-book/",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status="queued",
    )
    job = ProcessingJob.objects.create(submission=submission)
    output_dir = tmp_path / "legacy-output"

    sample = {
        "book_title": "কভারবিহীন বই",
        "author": "লেখক এক",
        "series": "",
        "book_type": "",
        "cover": None,
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "",
        "dedication": "",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [{"title": "অধ্যায় ১", "content": "<p>বিষয়বস্তু</p>", "type": "lesson", "parent": None}],
        "output_folder": str(output_dir),
    }

    def fake_scrape_book(_url):
        return sample

    def fake_generate_exports(_book_data):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text("<html><body>book</body></html>", encoding="utf-8")
        (output_dir / "কভারবিহীন বই.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr("apps.ingestion.services.submissions.scrape_book", fake_scrape_book)
    monkeypatch.setattr("apps.ingestion.services.submissions.generate_exports", fake_generate_exports)

    process_submission_job(str(job.id))

    book = Book.objects.get(title="কভারবিহীন বই")
    assert book.cover_source_url == ""


@pytest.mark.django_db
def test_successful_deleted_book_recreation_is_not_reprocessed_again(tmp_path, monkeypatch):
    user = User.objects.create_user(email="recreate-2001@example.com", password="strong-password-123")
    url = (
        "https://www.example.com/books/"
        "%E0%A7%A8%E0%A7%A6%E0%A7%A6%E0%A7%A7-%E0%A6%86-%E0%A6%B8%E0%A7%8D%E0%A6%AA%E0%A7%87%E0%A6%B8-"
        "%E0%A6%93%E0%A6%A1%E0%A6%BF%E0%A6%B8%E0%A6%BF-%E0%A6%86%E0%A6%B0%E0%A7%8D%E0%A6%A5%E0%A6%BE%E0%A6%B0/"
    )
    deleted_book = Book.objects.create(title="২০০১ : আ স্পেস ওডিসি", state="soft_deleted", review_state=ReviewState.APPROVED, source_site="example.com")
    Book.objects.filter(pk=deleted_book.pk).update(deleted_at=timezone.now())
    deleted_book.refresh_from_db()
    BookSource.objects.create(
        book=deleted_book,
        source_url=url,
        normalized_source_url=url,
        source_title=deleted_book.title,
    )
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input=url,
        normalized_input=normalize_text(url),
        resolved_url=url,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_confidence=1.0,
        status=SubmissionStatus.QUEUED,
        review_state=ReviewState.PENDING,
    )
    job = ProcessingJob.objects.create(submission=submission)

    sample = {
        "book_title": "২০০১ : আ স্পেস ওডিসি",
        "author": "আর্থার সি ক্লার্ক",
        "series": "",
        "book_type": "",
        "cover": "book_cover.jpg",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "",
        "dedication": "",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [{"title": "অধ্যায় ১", "content": "<p>বিষয়বস্তু</p>", "type": "lesson", "parent": None}],
        "output_folder": str(tmp_path),
    }

    monkeypatch.setattr("apps.ingestion.services.submissions.capture_source_page_metadata", lambda url: None)
    monkeypatch.setattr("apps.ingestion.services.submissions.scrape_book", lambda url: sample)

    def fake_generate_exports(book_data):
        output_dir = Path(book_data["output_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text("<html><body>book</body></html>", encoding="utf-8")
        (output_dir / "২০০১ : আ স্পেস ওডিসি.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr("apps.ingestion.services.submissions.generate_exports", fake_generate_exports)

    process_submission_job(str(job.id))
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.READY
    assert submission.raw_payload["served_from_database"] is False
    first_linked_book_id = submission.linked_book_id
    assert first_linked_book_id == deleted_book.id
    assert submission.linked_book.deleted_at is None

    repeated_job = process_submission_job(str(job.id))
    submission.refresh_from_db()

    assert repeated_job.id == job.id
    assert submission.status == SubmissionStatus.READY
    assert submission.raw_payload["served_from_database"] is False
    assert submission.linked_book_id == first_linked_book_id
    assert submission.linked_book.deleted_at is None
    assert BookSource.objects.get(normalized_source_url=url).book_id == first_linked_book_id
