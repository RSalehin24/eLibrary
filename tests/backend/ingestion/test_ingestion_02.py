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
def test_title_resolver_returns_ambiguous_matches_from_archive_bucket():
    page_one = """
    <div class="facetwp-template" data-name="books">
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="https://www.example.com/books/malice-one/">ম্যালিস - লেখক এক</a>
        </div>
      </div>
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="https://www.example.com/books/malice-two/">ম্যালিস - লেখক দুই</a>
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
            params = params or {}
            key = (params.get("_a_z", ""), params.get("_paged", 1))
            if key == ("ম", 1):
                return FakeResponse(page_one)
            return FakeResponse(empty_page)

    resolver = TitleResolver(session=FakeSession())

    result = resolver.resolve("ম্যালিস")

    assert result.status == "ambiguous"
    assert result.resolved_url == ""
    assert len(result.candidates) == 2
    assert {candidate["url"] for candidate in result.candidates} == {
        "https://www.example.com/books/malice-one/",
        "https://www.example.com/books/malice-two/",
    }


@pytest.mark.django_db
def test_title_resolver_enriches_candidates_from_book_page_metadata():
    archive_page = """
    <div class="facetwp-template" data-name="books">
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="https://www.example.com/books/malice/">ম্যালিস উপন্যাস - সৈকত মুখোপাধ্যায়</a>
        </div>
      </div>
    </div>
    """
    book_page = """
    <html>
      <head><title>ম্যালিস - সৈকত মুখোপাধ্যায়</title></head>
      <body>
        <div class="entry-meta entry-meta-after-content">
          <span class="entry-terms-authors"><a>সৈকত মুখোপাধ্যায়</a></span>
          <span class="entry-terms-series"><a>থ্রিলার</a></span>
        </div>
      </body>
    </html>
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
            params = params or {}
            if url == "https://www.example.com/books/malice/":
                return FakeResponse(book_page)
            key = (params.get("_a_z", ""), params.get("_paged", 1))
            if key == ("ম", 1):
                return FakeResponse(archive_page)
            return FakeResponse(empty_page)

    resolver = TitleResolver(session=FakeSession())

    result = resolver.resolve("ম্যালিস")

    assert result.status == "exact_match"
    assert result.resolved_url == "https://www.example.com/books/malice/"
    entry = SourceCatalogEntry.objects.get(source_url="https://www.example.com/books/malice/")
    assert entry.title == "ম্যালিস"
    assert entry.raw_data["metadata_source"] == "book_page"


@pytest.mark.django_db
def test_direct_url_submission_stores_source_page_metadata(monkeypatch):
    fake_metadata = {
        "source_url": "https://www.example.com/books/source-book/",
        "title": "সোর্স বুক",
        "author_line": "লেখক",
        "normalized_title": normalize_text("সোর্স বুক"),
        "normalized_display": normalize_text("সোর্স বুক লেখক"),
        "raw_data": {
            "title": "সোর্স বুক",
            "author_line": "লেখক",
            "metadata_source": "book_page",
        },
    }

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.capture_source_page_metadata",
        lambda url: fake_metadata,
    )

    submissions = create_submission_records(
        submitter=None,
        parsed_entries=[{"kind": "url", "value": "https://www.example.com/books/source-book/"}],
        auto_process=False,
    )

    assert submissions[0].raw_payload["source_page_metadata"]["title"] == "সোর্স বুক"


@pytest.mark.django_db
def test_source_catalog_refresh_starts_background_sync_and_returns_state(client, monkeypatch):
    admin = User.objects.create_superuser(email="catalog-refresh@example.com", password="strong-password-123")
    client.force_login(admin)

    monkeypatch.setattr("apps.ingestion.services.curation.dispatch_source_catalog_refresh", lambda state: state)

    response = client.post(
        "/api/ingestion/catalog/refresh/",
        data=json.dumps({"max_pages": 3}),
        content_type="application/json",
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["max_pages"] == 3
    assert payload["requested_by_email"] == admin.email

    sync_state = SourceCatalogRefreshState.objects.get(singleton_key="default")
    assert sync_state.status == SourceCatalogRefreshStatus.QUEUED
    assert sync_state.max_pages == 3
    assert sync_state.requested_by == admin


@pytest.mark.django_db
def test_source_catalog_entries_include_sync_state(client):
    admin = User.objects.create_superuser(email="catalog-sync-state@example.com", password="strong-password-123")
    client.force_login(admin)

    SourceCatalogRefreshState.objects.create(
        singleton_key="default",
        status=SourceCatalogRefreshStatus.PROCESSING,
        max_pages=6,
    )

    response = client.get("/api/ingestion/catalog/entries/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sync_state"]["status"] == "processing"
    assert payload["sync_state"]["max_pages"] == 6
