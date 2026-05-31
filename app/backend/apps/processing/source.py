from apps.catalog.models import GeneratedAssetType
from apps.catalog.services import (
    find_deleted_book_by_title,
    find_existing_book_by_source_url,
    replace_book_relations,
)
from django.conf import settings
from apps.ingestion.pipeline import epub_book, html_book, scraper
from apps.ingestion.pipeline.curated_pipeline import curate_book_document
from apps.ingestion.pipeline.curated_persistence import persist_curated_book as _persist_curated_book
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.ingestion.pipeline.scraper_support.text import normalize_text, texts_are_similar
from apps.ingestion.services.normalization import (
    clean_extracted_dedication_html,
    normalize_scraped_book,
)
from apps.ingestion.services.resolution_support import (
    fetch_source_page_metadata,
    upsert_source_catalog_entry,
)
from apps.ingestion.services.submissions_support.assets import sync_assets as _sync_assets
from apps.ingestion.services.submissions_support.detection import (
    detect_metadata_duplicate as _detect_metadata_duplicate,
    find_exact_existing_book as _find_exact_existing_book,
)
from apps.ingestion.services.submissions_support.persistence import (
    persist_scraped_book as _persist_scraped_book,
)


REQUIRED_GENERATED_ASSET_TYPES = (
    GeneratedAssetType.HTML,
    GeneratedAssetType.EPUB,
)
GENERATED_ASSET_LABELS = {
    GeneratedAssetType.HTML: "HTML",
    GeneratedAssetType.EPUB: "EPUB",
}


def capture_source_page_metadata(source_url):
    try:
        metadata = fetch_source_page_metadata(source_url)
    except Exception:
        return None

    upsert_source_catalog_entry(metadata)
    return metadata


def processing_scrape_limits():
    return {
        "max_nodes": getattr(settings, "PROCESSING_SCRAPER_MAX_NODES", 48),
        "max_depth": getattr(settings, "PROCESSING_SCRAPER_MAX_DEPTH", 3),
        "max_lesson_pages": getattr(
            settings,
            "PROCESSING_SCRAPER_MAX_LESSON_PAGES",
            2,
        ),
        "max_content_chars": getattr(
            settings,
            "PROCESSING_SCRAPER_MAX_CONTENT_CHARS",
            12000,
        ),
        "disable_recursive": getattr(
            settings,
            "PROCESSING_SCRAPER_DISABLE_RECURSIVE",
            False,
        ),
    }


def high_fidelity_scrape_limits():
    limits = scraper.normalize_scrape_limits(getattr(scraper, "DEFAULT_SCRAPE_LIMITS", {}))
    limits["disable_recursive"] = False
    return limits


def processing_curate_limits():
    """Content limits for the curate_book() pipeline in the processing worker.

    max_nodes defaults to None (unlimited) so that large books with many topics
    (e.g. 911 topics) are fully scraped.  Override via env vars if needed.
    """
    raw_max_nodes = getattr(settings, "PROCESSING_CURATE_MAX_NODES", None)
    try:
        max_nodes = int(raw_max_nodes) if raw_max_nodes is not None else None
    except (TypeError, ValueError):
        max_nodes = None
    return {
        "max_nodes": max_nodes,
        "max_depth": getattr(settings, "PROCESSING_CURATE_MAX_DEPTH", 6),
        "max_lesson_pages": getattr(settings, "PROCESSING_CURATE_MAX_LESSON_PAGES", 20),
        "max_content_chars": getattr(settings, "PROCESSING_CURATE_MAX_CONTENT_CHARS", 60000),
        "disable_recursive": False,
    }


def scrape_book(source_url):
    return scraper.scrape_book_data(
        normalize_source_url(source_url),
        content_limits=processing_scrape_limits(),
    )


def scrape_book_high_fidelity(source_url):
    return scraper.scrape_book_data(
        normalize_source_url(source_url),
        content_limits=high_fidelity_scrape_limits(),
    )


def generate_exports(book_data):
    html_book.create_html_book(book_data)
    epub_book.create_epub(book_data)


def curate_book(source_url, *, high_fidelity=False, content_limits=None, page_cache=None):
    if content_limits is not None:
        limits = content_limits
    elif high_fidelity:
        limits = high_fidelity_scrape_limits()
    else:
        limits = processing_curate_limits()
    return curate_book_document(
        normalize_source_url(source_url),
        content_limits=limits,
        page_cache=page_cache,
    )


def detect_metadata_duplicate(scraped_data):
    return _detect_metadata_duplicate(
        scraped_data,
        normalize_scraped_book_fn=normalize_scraped_book,
        texts_are_similar_fn=texts_are_similar,
    )


def find_exact_existing_book(scraped_data):
    return _find_exact_existing_book(
        scraped_data,
        normalize_scraped_book_fn=normalize_scraped_book,
    )


def sync_metadata_relations(book, normalized):
    return replace_book_relations(
        book,
        contributors=normalized["contributors"],
        series_names=normalized["series"],
        category_names=normalized["categories"],
    )


def persist_scraped_book(submission, job, scraped_data, target_book=None):
    return _persist_scraped_book(
        submission,
        scraped_data,
        clean_extracted_dedication_html_fn=clean_extracted_dedication_html,
        find_deleted_book_by_title_fn=find_deleted_book_by_title,
        find_existing_book_by_source_url_fn=find_existing_book_by_source_url,
        job=job,
        normalize_scraped_book_fn=normalize_scraped_book,
        normalize_source_url_fn=normalize_source_url,
        sync_metadata_relations_fn=sync_metadata_relations,
        target_book=target_book,
    )


def persist_curated_book(submission, job, curated_result, target_book=None):
    return _persist_curated_book(
        curated_result,
        source_url=submission.resolved_url,
        job=job,
        target_book=target_book,
    )


def sync_assets(book, job, scraped_data):
    return _sync_assets(
        book,
        job,
        scraped_data,
        generated_asset_labels=GENERATED_ASSET_LABELS,
        required_asset_types=REQUIRED_GENERATED_ASSET_TYPES,
    )


__all__ = [
    "capture_source_page_metadata",
    "curate_book",
    "detect_metadata_duplicate",
    "find_exact_existing_book",
    "generate_exports",
    "normalize_source_url",
    "normalize_text",
    "persist_scraped_book",
    "persist_curated_book",
    "scrape_book",
    "scrape_book_high_fidelity",
    "sync_assets",
    "texts_are_similar",
    "upsert_source_catalog_entry",
]
