from urllib.parse import urljoin

from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.ingestion.services.resolution_support_metadata import (
    metadata_entry_defaults,
    split_display_title,
)
from apps.ingestion.source_processing.policy import require_source_url, source_hosts
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .configuration import MAX_PAGE_ENTRIES


def discovered_entry(anchor, url):
    href = anchor.get("href")
    if not isinstance(href, str) or not href.strip():
        raise ExecutionFailure(
            FailureKind.PERMANENT, "source_discovery_metadata_invalid"
        )
    candidate = urljoin(url, href)
    require_source_url(candidate, source_hosts())
    source_url = normalize_source_url(candidate)
    require_source_url(source_url, source_hosts())
    title, author = split_display_title(anchor.get_text(" ", strip=True))
    if not title or len(title) > 255 or len(author) > 255 or len(source_url) > 1000:
        raise ExecutionFailure(
            FailureKind.PERMANENT, "source_discovery_metadata_invalid"
        )
    return metadata_entry_defaults(
        source_url, title, author, {"metadata_source": "catalog_archive"}
    )


def discovery_page(soup, url):
    if soup.select_one('input[type="password"]'):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_authentication_required")
    anchors = soup.select(
        ".entry-title a[href], article h2 a[href], article h3 a[href]"
    )
    if len(anchors) > MAX_PAGE_ENTRIES:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_catalog_page_too_large")
    entries = {}
    for anchor in anchors:
        entry = discovered_entry(anchor, url)
        entries[entry["source_url"]] = entry
    next_link = soup.select_one(
        'a[rel~="next"][href], a.next.page-numbers[href], .pagination a.next[href]'
    )
    next_url = urljoin(url, next_link["href"]) if next_link else None
    if next_url:
        require_source_url(next_url, source_hosts())
    return list(entries.values()), next_url
