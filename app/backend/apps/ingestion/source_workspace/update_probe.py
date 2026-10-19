import json
from hashlib import sha256

from bs4 import BeautifulSoup
from django.utils.dateparse import parse_datetime

from apps.ingestion.pipeline.book_manifest import (
    extract_entry_content_html,
    pagination_data,
)
from apps.ingestion.pipeline.scraper_support.network import normalize_crawl_url
from apps.ingestion.source_processing.content_text import canonical_text
from apps.ingestion.source_processing.storage import read_artifact


def source_chapter_url(value, url):
    try:
        return normalize_crawl_url(value, url)
    except ValueError:
        return ""


def source_update_probe(soup, url):
    chapters = {
        source_chapter_url(anchor.get("href", ""), url)
        for anchor in soup.select('a[href*="/lessons/"], a[href*="/topics/"]')
    }
    chapters.discard("")
    pagers = [
        {key: values.get(key) for key in ("total_items", "total_pages")}
        for pager in soup.select(".ld-pagination[data-pager-results]")
        if (values := pagination_data(pager))
    ]
    modified = soup.select_one(
        'meta[property="article:modified_time"],meta[name="last-modified"]'
    )
    body = canonical_text(extract_entry_content_html(soup))
    evidence = {
        "body": body,
        "chapters": sorted(chapters),
        "pagers": pagers,
        "modified": modified.get("content", "") if modified else "",
    }
    signature = sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    try:
        parsed_modified = (
            parse_datetime(evidence["modified"]) if evidence["modified"] else None
        )
    except (TypeError, ValueError):
        parsed_modified = None
    return {
        "signature": signature,
        "chapter_count": len(chapters),
        "source_modified_at": parsed_modified.isoformat() if parsed_modified else None,
    }


def cached_source_probe(job, url):
    reference = job.checkpoint.get("page_cache_ref")
    if not reference:
        return None
    pages = read_artifact(job.pk, reference)
    landing = pages.get(url)
    if landing:
        return source_update_probe(
            BeautifulSoup(read_artifact(job.pk, landing), "html.parser"), url
        )
    return None
