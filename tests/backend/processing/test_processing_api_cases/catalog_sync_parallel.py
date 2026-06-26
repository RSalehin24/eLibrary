
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.processing import services as processing_services


def _fake_entry(source_url, title="Fake Title", author_line="Fake Author"):
    return {
        "source_url": source_url,
        "title": title,
        "author_line": author_line,
        "raw_data": {"metadata_source": "archive_page"},
    }


def _fake_metadata(source_url, title="Fake Title", author_line="Fake Author"):
    return {
        "source_url": source_url,
        "title": title,
        "author_line": author_line,
        "raw_data": {"metadata_source": "archive_page"},
    }


def _fake_entry_model(source_url, title="Fake Title", author_line="Fake Author"):
    now = timezone.now()
    return SimpleNamespace(
        id="uuid-fake",
        title=title,
        source_url=source_url,
        author_line=author_line,
        raw_data={"metadata_source": "archive_page"},
        updated_at=now,
    )


def _fake_payload(source_url, title="Fake Title"):
    return {
        "id": "uuid-fake",
        "name": title,
        "url": source_url,
        "displayUrl": source_url,
        "displayPath": "books/fake",
        "category": "Uncategorized",
        "writer": "Fake Author",
        "translator": "",
        "composer": "",
        "publisher": "",
        "updatedAt": timezone.now().isoformat(),
        "wasIncomplete": False,
        "willResolveToCategory": "",
    }


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def mock_dependencies(
    monkeypatch,
    *,
    entries_by_page,
    concurrency=1,
    fail_on_page=None,
    fail_on_url=None,
):
    def fake_create_session():
        return SimpleNamespace(headers={})

    def fake_archive_query_params(self, page_number=1):
        return {"page": page_number, "q": "test"}

    def fake_get_with_host_fallback(session, url, params=None, timeout=30):
        page_number = (params or {}).get("page", 1)
        idx = page_number - 1
        if fail_on_page is not None and idx == fail_on_page:
            raise Exception("Simulated fetch failure")
        session._page = page_number
        return FakeResponse()

    def fake_parse_catalog_page(self, soup):
        page_number = getattr(self.session, "_page", 1)
        idx = page_number - 1
        if idx < len(entries_by_page):
            return entries_by_page[idx]
        return []

    def fake_fetch_metadata(source_url, session=None):
        if fail_on_url is not None and source_url == fail_on_url:
            raise Exception("Simulated metadata failure")
        return _fake_metadata(source_url)

    def fake_upsert_entry(metadata):
        return _fake_entry_model(
            metadata["source_url"], metadata["title"], metadata["author_line"]
        )

    def fake_entry_payload(entry):
        return _fake_payload(entry.source_url, entry.title)

    def fake_upsert_remote(payloads):
        return {
            "appended_count": len(payloads),
            "updated_count": 0,
            "skipped_count": 0,
        }

    monkeypatch.setattr(
        "apps.processing.services.create_session_with_retries",
        fake_create_session,
    )
    monkeypatch.setattr(
        "apps.processing.services.TitleResolver.archive_query_params",
        fake_archive_query_params,
    )
    monkeypatch.setattr(
        "apps.processing.services.TitleResolver.parse_catalog_page",
        fake_parse_catalog_page,
    )
    monkeypatch.setattr(
        "apps.processing.services.get_with_host_fallback",
        fake_get_with_host_fallback,
    )
    monkeypatch.setattr(
        "apps.processing.services.fetch_source_page_metadata",
        fake_fetch_metadata,
    )
    monkeypatch.setattr(
        "apps.processing.services.upsert_source_catalog_entry",
        fake_upsert_entry,
    )
    monkeypatch.setattr(
        "apps.processing.services.source_catalog_entry_payload",
        fake_entry_payload,
    )
    monkeypatch.setattr(
        "apps.processing.services.upsert_remote_records",
        fake_upsert_remote,
    )


class TestRefreshCatalogParallel:
    def test_empty_catalog_returns_zeros(self, monkeypatch):
        mock_dependencies(monkeypatch, entries_by_page=[[]])
        result = processing_services.refresh_catalog_parallel(concurrency=1)
        assert result == {"appended_count": 0, "updated_count": 0, "total": 0}

    def test_single_page_with_entries(self, monkeypatch):
        entries = [
            [
                _fake_entry("https://archive.org/details/book1"),
                _fake_entry("https://archive.org/details/book2"),
            ],
        ]
        mock_dependencies(monkeypatch, entries_by_page=entries)
        result = processing_services.refresh_catalog_parallel(concurrency=1)
        assert result["total"] == 2
        assert result["appended_count"] == 2

    def test_stops_at_empty_page(self, monkeypatch):
        entries = [
            [_fake_entry("https://archive.org/details/book1")],
            [_fake_entry("https://archive.org/details/book2")],
            [_fake_entry("https://archive.org/details/book3")],
            [],
        ]
        mock_dependencies(monkeypatch, entries_by_page=entries)
        result = processing_services.refresh_catalog_parallel(concurrency=1)
        assert result["total"] == 3

    def test_duplicate_urls_deduplicated(self, monkeypatch):
        entries = [
            [_fake_entry("https://archive.org/details/book1")],
            [_fake_entry("https://archive.org/details/book1")],
            [_fake_entry("https://archive.org/details/book2")],
            [],
        ]
        mock_dependencies(monkeypatch, entries_by_page=entries)
        result = processing_services.refresh_catalog_parallel(concurrency=1)
        assert result["total"] == 2

    def test_failed_entry_metadata_skips_entry(self, monkeypatch):
        entries = [
            [
                _fake_entry("https://archive.org/details/book1"),
                _fake_entry("https://archive.org/details/book2"),
                _fake_entry("https://archive.org/details/book3"),
            ],
        ]
        mock_dependencies(
            monkeypatch,
            entries_by_page=entries,
            fail_on_url="https://archive.org/details/book2",
        )
        result = processing_services.refresh_catalog_parallel(concurrency=1)
        assert result["total"] == 2
        assert result["appended_count"] == 2

    def test_failed_page_fetch_skips_page(self, monkeypatch):
        entries = [
            [_fake_entry("https://archive.org/details/book1")],
            [_fake_entry("https://archive.org/details/book2")],
            [],
        ]
        mock_dependencies(monkeypatch, entries_by_page=entries, fail_on_page=0)
        result = processing_services.refresh_catalog_parallel(concurrency=1)
        assert result["total"] == 1
        assert result["appended_count"] == 1
