from apps.ingestion.pipeline.scraper_support import network
from apps.processing import source


def test_processing_source_helpers_bypass_legacy_adapter(monkeypatch):
    adapter_failure = AssertionError("legacy adapter should not be used by processing source helpers")

    monkeypatch.setattr(
        "apps.ingestion.services.legacy_adapter.normalize_source_url",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(adapter_failure),
        raising=False,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.legacy_adapter.scrape_book",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(adapter_failure),
        raising=False,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.legacy_adapter.generate_exports",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(adapter_failure),
        raising=False,
    )

    scrape_calls = []
    html_calls = []
    epub_calls = []

    def fake_scrape_book_data(url, **kwargs):
        scrape_calls.append((url, kwargs))
        return {"resolved_url": url}

    monkeypatch.setattr(
        "apps.processing.source.scraper.scrape_book_data",
        fake_scrape_book_data,
    )
    monkeypatch.setattr(
        "apps.processing.source.html_book.create_html_book",
        lambda book_data: html_calls.append(book_data),
    )
    monkeypatch.setattr(
        "apps.processing.source.epub_book.create_epub",
        lambda book_data: epub_calls.append(book_data),
    )

    normalized_url = source.normalize_source_url(
        "https://example.com/books/example-book"
    )
    assert normalized_url == "https://www.example.com/books/example-book/"

    scraped = source.scrape_book("https://example.com/books/example-book")
    assert scraped == {"resolved_url": normalized_url}
    assert len(scrape_calls) == 1
    called_url, called_kwargs = scrape_calls[0]
    assert called_url == normalized_url
    assert called_kwargs == {
        "content_limits": {
            "max_nodes": 48,
            "max_depth": 3,
            "max_lesson_pages": 2,
            "max_content_chars": 12000,
            "disable_recursive": False,
        }
    }

    payload = {"book_title": "Example Book", "output_folder": "/tmp/example"}
    source.generate_exports(payload)
    assert html_calls == [payload]
    assert epub_calls == [payload]


def test_processing_source_scrape_limits_can_be_configured(settings):
    settings.PROCESSING_SCRAPER_MAX_NODES = 144
    settings.PROCESSING_SCRAPER_MAX_DEPTH = 4
    settings.PROCESSING_SCRAPER_MAX_LESSON_PAGES = 12
    settings.PROCESSING_SCRAPER_MAX_CONTENT_CHARS = 18000
    settings.PROCESSING_SCRAPER_DISABLE_RECURSIVE = False

    assert source.processing_scrape_limits() == {
        "max_nodes": 144,
        "max_depth": 4,
        "max_lesson_pages": 12,
        "max_content_chars": 18000,
        "disable_recursive": False,
    }


def test_processing_source_high_fidelity_scrape_uses_large_recursive_defaults(monkeypatch):
    scrape_calls = []

    monkeypatch.setattr(
        "apps.processing.source.scraper.scrape_book_data",
        lambda url, **kwargs: scrape_calls.append((url, kwargs)) or {"resolved_url": url},
    )

    normalized_url = source.normalize_source_url(
        "https://example.com/books/high-fidelity-book"
    )
    scraped = source.scrape_book_high_fidelity(
        "https://example.com/books/high-fidelity-book"
    )

    assert scraped == {"resolved_url": normalized_url}
    assert scrape_calls == [
        (
            normalized_url,
            {
                "content_limits": {
                    "max_nodes": 320,
                    "max_depth": 6,
                    "max_lesson_pages": 20,
                    "max_content_chars": 120000,
                    "disable_recursive": False,
                }
            },
        )
    ]


def test_get_soup_uses_host_fallback_and_decodes_bangla_html(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class FakeResponse:
        status_code = 200
        headers = {}
        encoding = None
        apparent_encoding = None
        content = (
            "<html><body><h1>অ-আ-ক-খুনের কাঁটা – নারায়ণ সান্যাল</h1></body></html>"
        ).encode("utf-8")

    session = FakeSession()
    calls = []

    monkeypatch.setattr(
        "apps.ingestion.pipeline.scraper_support.network.create_session_with_retries",
        lambda retries=3, backoff_factor=1: session,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.resolution_support_network.get_with_host_fallback",
        lambda session_obj, url, **kwargs: calls.append((session_obj, url, kwargs))
        or FakeResponse(),
    )

    soup = network.get_soup("https://www.example.com/books/bangla-book/")

    assert soup is not None
    assert soup.find("h1").get_text(strip=True) == "অ-আ-ক-খুনের কাঁটা – নারায়ণ সান্যাল"
    assert calls == [
        (
            session,
            "https://www.example.com/books/bangla-book/",
            {"headers": network.HEADERS, "timeout": 30},
        )
    ]
    assert session.closed is True
