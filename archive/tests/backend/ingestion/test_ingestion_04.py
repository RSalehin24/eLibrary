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
def test_incomplete_catalog_check_uses_book_contributors_for_author_line(client):
    admin = User.objects.create_superuser(email="incomplete-check@example.com", password="strong-password-123")
    client.force_login(admin)

    category = Category.objects.create(name="অসম্পূর্ণ বই")
    contributor = Contributor.objects.create(name="Writer One")
    book = Book.objects.create(title="Incomplete Book")
    book.categories.add(category)
    BookContributor.objects.create(book=book, contributor=contributor, role="author", sort_order=0)

    source_url = "https://www.example.com/books/incomplete-book/"
    BookSource.objects.create(
        book=book,
        source_url=source_url,
        normalized_source_url=source_url,
    )
    SourceCatalogEntry.objects.create(
        source_url=source_url,
        title="Incomplete Book",
        author_line="Writer One",
        normalized_title=normalize_text("Incomplete Book"),
        normalized_display=normalize_text("Incomplete Book Writer One"),
        raw_data={"category": "অসম্পূর্ণ বই"},
    )

    submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input=source_url,
        normalized_input="incomplete book",
        resolved_url=source_url,
        origin=SubmissionOrigin.CURATION,
        status=SubmissionStatus.QUEUED,
    )
    ProcessingJob.objects.create(
        submission=submission,
        book=book,
        status=JobStatus.QUEUED,
    )

    response = client.get("/api/ingestion/catalog/incomplete-check/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["queued"] == 1
    assert payload["entries"][0]["book_title"] == "Incomplete Book"
    assert payload["entries"][0]["author_line"] == "Writer One"


@pytest.mark.django_db
def test_title_resolver_refresh_catalog_accepts_long_source_urls():
    long_slug = "kaliguneen-" + ("rahasya-" * 24)
    long_url = f"https://www.example.com/books/{long_slug}/"
    page_one = f"""
    <div class="facetwp-template" data-name="books">
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="{long_url}">কালীগুণীন ও বজ্র-সিন্দুক রহস্য - সৌমিক দে</a>
        </div>
      </div>
    </div>
    """
    empty_page = '<div class="facetwp-template" data-name="books"></div>'

    class FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def get(self, url, params=None, timeout=30):
            page_number = (params or {}).get("_paged", 1)
            return FakeResponse(page_one if page_number == 1 else empty_page)

    resolver = TitleResolver(session=FakeSession())

    refreshed = resolver.refresh_catalog(max_pages=2)

    assert len(refreshed) == 1
    entry = SourceCatalogEntry.objects.get(source_url=long_url)
    assert entry.title == "কালীগুণীন ও বজ্র-সিন্দুক রহস্য"
    assert entry.author_line == "সৌমিক দে"


@pytest.mark.django_db
def test_title_resolver_refresh_catalog_continues_past_existing_first_page_entries():
    existing_url = "https://www.example.com/books/existing-book/"
    new_url = "https://www.example.com/books/new-book/"
    SourceCatalogEntry.objects.create(
        source_url=existing_url,
        title="Existing Book",
        author_line="Known Author",
        normalized_title=normalize_text("Existing Book"),
        normalized_display=normalize_text("Existing Book Known Author"),
    )

    first_page = f"""
    <div class="facetwp-template" data-name="books">
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="{existing_url}">Existing Book - Known Author</a>
        </div>
      </div>
    </div>
    """
    second_page = f"""
    <div class="facetwp-template" data-name="books">
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="{new_url}">New Book - New Author</a>
        </div>
      </div>
    </div>
    """

    class FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self):
            self.headers = {}
            self.calls = []

        def get(self, url, params=None, timeout=30):
            params = params or {}
            self.calls.append((url, params))
            page_number = params.get("_paged", 1)
            if page_number == 1:
                return FakeResponse(first_page)
            return FakeResponse(second_page)

    session = FakeSession()
    resolver = TitleResolver(session=session)

    refreshed = resolver.refresh_catalog(max_pages=2)

    assert refreshed == [
        {
            "source_url": new_url,
            "title": "New Book",
            "author_line": "New Author",
            "normalized_title": normalize_text("New Book"),
            "normalized_display": normalize_text("New Book New Author"),
            "raw_data": {
                "title": "New Book",
                "display_title": "New Book - New Author",
                "author_line": "New Author",
                "metadata_source": "archive_page",
            },
        }
    ]
    assert session.calls == [
        (CATALOG_URL, {}),
        (CATALOG_URL, {"_paged": 2}),
    ]
    assert SourceCatalogEntry.objects.filter(source_url=new_url).count() == 1
