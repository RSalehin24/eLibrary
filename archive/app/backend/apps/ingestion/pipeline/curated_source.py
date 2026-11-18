from apps.ingestion.pipeline.book_manifest import (
    CURRENT_MANIFEST_SCHEMA_VERSION,
    build_manifest_source_pages,
)
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url


CURATED_DOCUMENT_SCHEMA_VERSION = CURRENT_MANIFEST_SCHEMA_VERSION


def fetch_source_pages(source_url, *, content_limits=None, page_cache=None):
    canonical_url = normalize_source_url(source_url)
    return build_manifest_source_pages(
        canonical_url,
        content_limits=content_limits,
        page_cache=page_cache,
    )


def build_source_snapshot(source_pages):
    scraped_data = source_pages.get("raw_scrape_payload") or {}
    fetched_urls = {source_pages.get("canonical_url", "")}
    for page in source_pages.get("pages", []) or []:
        if (page or {}).get("status") == "fetched" and (page or {}).get("url"):
            fetched_urls.add(page["url"])
    for item in scraped_data.get("content_items", []) or []:
        source_url = (item or {}).get("source_url") or ""
        if source_url:
            fetched_urls.add(source_url)

    return {
        "schema_version": source_pages.get("schema_version", CURATED_DOCUMENT_SCHEMA_VERSION),
        "source_url": source_pages.get("source_url", ""),
        "canonical_url": source_pages.get("canonical_url", ""),
        "pages": source_pages.get("pages", []),
        "fetched_urls": sorted(url for url in fetched_urls if url),
        "manifest": source_pages.get("manifest") or {},
        "raw_scrape_payload": scraped_data,
    }
