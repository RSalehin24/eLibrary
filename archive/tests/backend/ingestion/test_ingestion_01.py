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


def test_legacy_normalize_text_preserves_bengali_combining_marks():
    assert normalize_text("ম্যালিস") == "ম্যালিস"


def test_get_with_host_fallback_uses_direct_ip_when_dns_resolution_fails(monkeypatch):
    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeSession:
        def __init__(self):
            self.headers = {}
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            raise requests.exceptions.ConnectionError(
                "HTTPSConnection(host='example.com'): Failed to resolve host (Name resolution)"
            )

    session = FakeSession()
    direct_calls = []

    monkeypatch.setattr(
        "apps.ingestion.services.resolution.resolve_host_with_dns_fallback",
        lambda host: ["104.21.81.247"] if host == "www.example.com" else [],
    )

    def fake_direct_ip_request(session_obj, url, host, ip, **kwargs):
        direct_calls.append((url, host, ip, kwargs.get("params")))
        return FakeResponse("ok-from-direct-ip")

    monkeypatch.setattr(
        "apps.ingestion.services.resolution.get_via_direct_ip_https",
        fake_direct_ip_request,
    )

    response = get_with_host_fallback(
        session,
        "https://www.example.com/books/",
        params={"_a_z": "ম"},
        timeout=30,
    )

    assert response.text == "ok-from-direct-ip"
    assert len(session.calls) >= 1
    assert direct_calls
    assert direct_calls[0][1] == "www.example.com"
    assert direct_calls[0][2] == "104.21.81.247"


def test_get_with_host_fallback_does_not_mask_non_dns_connection_errors(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.headers = {}

        def get(self, _url, **_kwargs):
            raise requests.exceptions.ConnectionError("Connection reset by peer")

    monkeypatch.setattr(
        "apps.ingestion.services.resolution.get_via_direct_ip_https",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("direct IP fallback should not run")),
    )

    with pytest.raises(requests.exceptions.ConnectionError, match="Connection reset by peer"):
        get_with_host_fallback(FakeSession(), "https://www.example.com/books/", timeout=30)


@pytest.mark.django_db
def test_title_submission_surfaces_exact_match_without_guessing(client, settings, monkeypatch):
    settings.CELERY_TASK_ALWAYS_EAGER = False
    user = User.objects.create_user(email="submitter@example.com", password="strong-password-123")
    client.force_login(user)

    SourceCatalogEntry.objects.create(
        source_url="https://www.example.com/books/sample-book/",
        title="স্যাম্পল বুক",
        author_line="লেখক",
        normalized_title=normalize_text("স্যাম্পল বুক"),
        normalized_display=normalize_text("স্যাম্পল বুক লেখক"),
    )

    response = client.post(
        "/api/ingestion/submissions/",
        data=json.dumps(
            {
                "input_type": "title",
                "content": "স্যাম্পল বুক",
                "auto_process": False,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()[0]
    assert payload["resolution_status"] == "exact_match"
    assert payload["status"] == "queued"
    assert payload["resolved_url"] == "https://www.example.com/books/sample-book/"


@pytest.mark.django_db
def test_submission_bulk_status_returns_requested_visible_submissions_in_order(client):
    user = User.objects.create_user(email="bulk-status@example.com", password="strong-password-123")
    other_user = User.objects.create_user(email="bulk-status-other@example.com", password="strong-password-123")
    first = BookSubmission.objects.create(
        submitter=user,
        input_type="title",
        original_input="প্রথম",
        normalized_input="প্রথম",
        status=SubmissionStatus.QUEUED,
    )
    second = BookSubmission.objects.create(
        submitter=user,
        input_type="title",
        original_input="দ্বিতীয়",
        normalized_input="দ্বিতীয়",
        status=SubmissionStatus.PROCESSING,
    )
    hidden = BookSubmission.objects.create(
        submitter=other_user,
        input_type="title",
        original_input="লুকানো",
        normalized_input="লুকানো",
        status=SubmissionStatus.READY,
    )
    client.force_login(user)

    response = client.post(
        "/api/ingestion/submissions/status/",
        data=json.dumps({"ids": [str(second.id), str(hidden.id), str(first.id)]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()] == [str(second.id), str(first.id)]


@pytest.mark.django_db
def test_title_resolver_crawls_archive_bucket_pages_and_splits_author_from_display_title():
    page_one = """
    <div class="facetwp-template" data-name="books">
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="https://www.example.com/books/other-book/">মেঘ - লেখক এক</a>
        </div>
      </div>
    </div>
    """
    page_two = """
    <div class="facetwp-template" data-name="books">
      <div class="fwpl-result">
        <div class="fwpl-item el-97dha">
          <a href="https://www.example.com/books/malice/">ম্যালিস - সৈকত মুখোপাধ্যায়</a>
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
            self.calls = []

        def get(self, url, params=None, timeout=30):
            params = params or {}
            self.calls.append((url, params))
            key = (params.get("_a_z", ""), params.get("_paged", 1))
            mapping = {
                ("ম", 1): page_one,
                ("ম", 2): page_two,
                ("ম", 3): empty_page,
            }
            return FakeResponse(mapping.get(key, empty_page))

    session = FakeSession()
    resolver = TitleResolver(session=session)

    result = resolver.resolve("ম্যালিস")

    assert result.status == "exact_match"
    assert result.resolved_url == "https://www.example.com/books/malice/"
    entry = SourceCatalogEntry.objects.get(source_url="https://www.example.com/books/malice/")
    assert entry.title == "ম্যালিস"
    assert entry.author_line == "সৈকত মুখোপাধ্যায়"
    assert ("https://www.example.com/books/", {"_a_z": "ম"}) in session.calls
    assert ("https://www.example.com/books/", {"_a_z": "ম", "_paged": 2}) in session.calls
