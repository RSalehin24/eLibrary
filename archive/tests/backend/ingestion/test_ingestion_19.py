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
def test_process_submission_job_replaces_existing_media_assets_instead_of_creating_duplicates(tmp_path, settings, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"

    user = User.objects.create_user(email="replace-assets@example.com", password="strong-password-123")
    output_dir = tmp_path / "legacy-output"

    submission_one = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/reprocess-book/",
        normalized_input="reprocess book",
        resolved_url="https://www.example.com/books/reprocess-book/",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status="queued",
    )
    first_job = ProcessingJob.objects.create(submission=submission_one)

    first_scraped = {
        "book_title": "পুনরায় বই",
        "author": "লেখক এক",
        "series": "",
        "book_type": "",
        "cover": "book_cover.jpg",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "",
        "dedication": "",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [{"title": "অধ্যায় ১", "content": "<p>বিষয়বস্তু</p>", "type": "lesson", "parent": None}],
        "output_folder": str(output_dir),
    }

    def fake_scrape_book(url):
        return first_scraped

    def fake_generate_exports(book_data):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text("<html><body>first</body></html>", encoding="utf-8")
        (output_dir / "পুনরায় বই.epub").write_bytes(b"first")
        (output_dir / "book_cover.jpg").write_bytes(b"first")

    monkeypatch.setattr("apps.ingestion.services.submissions.scrape_book", fake_scrape_book)
    monkeypatch.setattr("apps.ingestion.services.submissions.generate_exports", fake_generate_exports)

    process_submission_job(str(first_job.id))

    book = Book.objects.get()
    second_job = ProcessingJob.objects.create(submission=submission_one, job_type="ingestion")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "book.html").write_text("<html><body>second</body></html>", encoding="utf-8")
    (output_dir / "পুনরায় বই.epub").write_bytes(b"second")
    (output_dir / "book_cover.jpg").write_bytes(b"second")

    sync_assets(
        book,
        second_job,
        {
            **first_scraped,
            "output_folder": str(output_dir),
        },
    )

    media_dir = Path(settings.MEDIA_ROOT) / "generated" / book.slug
    saved_paths = sorted(media_dir.iterdir())
    saved_names = [path.name for path in saved_paths]
    assert "book.html" in saved_names
    assert "book_cover.jpg" in saved_names
    assert len([name for name in saved_names if name.endswith(".epub")]) == 1
    assert len(saved_names) == 3
    assert (media_dir / "book.html").read_text(encoding="utf-8") == "<html><body>second</body></html>"
    cover_path = media_dir / "book_cover.jpg"
    assert cover_path.read_bytes() == b"second"
    assert not output_dir.exists()


@pytest.mark.django_db
def test_url_submission_checks_database_first_and_returns_existing_book(client):
    user = User.objects.create_user(email="existing-url@example.com", password="strong-password-123")
    existing_book = Book.objects.create(title="সংরক্ষিত বই", state="ready", review_state="approved")
    BookSource.objects.create(
        book=existing_book,
        source_url="https://www.example.com/books/existing-book/",
        normalized_source_url="https://www.example.com/books/existing-book/",
        source_title="সংরক্ষিত বই",
    )
    client.force_login(user)

    response = client.post(
        "/api/ingestion/submissions/",
        data=json.dumps(
            {
                "input_type": "url",
                "content": "https://www.example.com/books/existing-book/",
                "auto_process": True,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()[0]
    assert payload["status"] == "ready"
    assert payload["served_from_database"] is True
    assert payload["linked_book_slug"] == existing_book.slug
    assert ProcessingJob.objects.count() == 0
    assert PreviewAccessSession.objects.filter(user=user, book=existing_book).exists()


@pytest.mark.django_db
def test_title_submission_requires_resolution_instead_of_local_title_only_reuse(client):
    user = User.objects.create_user(email="existing-title@example.com", password="strong-password-123")
    existing_book = Book.objects.create(title="একই বই", state="ready", review_state="approved")
    client.force_login(user)

    response = client.post(
        "/api/ingestion/submissions/",
        data=json.dumps(
            {
                "input_type": "title",
                "content": "একই বই",
                "auto_process": True,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()[0]
    assert payload["served_from_database"] is False
    assert payload["linked_book_slug"] == ""
    assert payload["status"] in {"queued", "processing", "needs_review", "ready"}


@pytest.mark.django_db
def test_processing_reuses_canonical_author_series_and_category_names(tmp_path, monkeypatch):
    user = User.objects.create_user(email="canonical@example.com", password="strong-password-123")
    submission = BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/canonical-book/",
        normalized_input="canonical book",
        resolved_url="https://www.example.com/books/canonical-book/",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status="queued",
    )
    job = ProcessingJob.objects.create(submission=submission)

    sample = {
        "book_title": "ক্যানোনিক্যাল বই",
        "author": "লেখক এক, লেখক-এক, লেখক এক",
        "series": "রহস্য সিরিজ, রহস্য-সিরিজ",
        "book_type": "উপন্যাস, উপন্যাস",
        "cover": "book_cover.jpg",
        "main_content": "<p>মূল অংশ</p>",
        "book_info": "<p>অনুবাদ: অনুবাদক এক, অনুবাদক-এক</p>",
        "dedication": "<p>উৎসর্গ</p>",
        "toc": [{"title": "অধ্যায় ১", "type": "lesson", "has_content": True}],
        "content_items": [{"title": "অধ্যায় ১", "content": "<p>বিষয়বস্তু</p>", "type": "lesson", "parent": None}],
        "output_folder": str(tmp_path),
    }

    def fake_scrape_book(url):
        return sample

    def fake_generate_exports(book_data):
        output_dir = Path(book_data["output_folder"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "book.html").write_text("<html><body>book</body></html>", encoding="utf-8")
        (output_dir / "ক্যানোনিক্যাল বই.epub").write_bytes(b"epub-bytes")
        (output_dir / "book_cover.jpg").write_bytes(b"cover-bytes")

    monkeypatch.setattr("apps.ingestion.services.submissions.scrape_book", fake_scrape_book)
    monkeypatch.setattr("apps.ingestion.services.submissions.generate_exports", fake_generate_exports)

    process_submission_job(str(job.id))

    assert Contributor.objects.filter(normalized_name=normalize_text("লেখক এক")).count() == 1
    assert Contributor.objects.filter(normalized_name=normalize_text("অনুবাদক এক")).count() == 1
    assert Series.objects.filter(normalized_name=normalize_text("রহস্য সিরিজ")).count() == 1
    assert Category.objects.filter(normalized_name=normalize_text("উপন্যাস")).count() == 1
