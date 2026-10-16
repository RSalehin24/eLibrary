from apps.ingestion.pipeline.scraper_modules import (
    book_scrape_entrypoint,
    lesson_collection,
    metadata_and_inline_toc,
    recursive_content_nodes,
    scrape_limits_and_header_cleanup,
)


def patch_scraper(monkeypatch, name, replacement):
    """Replace a shared dependency at each explicit consuming import."""
    for module in (
        book_scrape_entrypoint,
        lesson_collection,
        metadata_and_inline_toc,
        recursive_content_nodes,
        scrape_limits_and_header_cleanup,
    ):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, replacement)
