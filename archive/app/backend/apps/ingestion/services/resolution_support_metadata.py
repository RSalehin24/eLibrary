import re

import requests
from bs4 import BeautifulSoup

from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.ingestion.pipeline.scraper_support.text import normalize_text
from apps.ingestion.services.normalization_support.metadata import (
    extract_contributor_evidence,
)
from apps.ingestion.services.resolution_support_hosts import SEARCH_HEADERS
from apps.ingestion.services.resolution_support_network import get_with_host_fallback

DISPLAY_TITLE_SEPARATOR_PATTERN = re.compile(r"\s+[–—-]\s+")
NON_CONTRIBUTOR_TITLE_SUFFIXES = (
    "খণ্ড",
    "পর্ব",
    "অধ্যায়",
    "অধ্যায়",
    "সংস্করণ",
    "গল্প",
    "ছোটগল্প",
    "উপন্যাস",
    "প্রবন্ধ",
    "কাহিনি",
    "কাহিনী",
    "সাহিত্য",
    "ইতিহাস",
    "দর্শন",
    "edition",
    "volume",
    "vol",
    "part",
    "series",
    "সমগ্র",
)


def metadata_entry_defaults(source_url, title, author_line="", raw_data=None):
    normalized_title = normalize_text(title)
    display_parts = [title, author_line]
    return {
        "source_url": source_url,
        "title": title,
        "author_line": author_line,
        "normalized_title": normalized_title,
        "normalized_display": normalize_text(" ".join(part for part in display_parts if part)),
        "raw_data": raw_data or {},
    }


def trailing_looks_like_contributor_phrase(text):
    cleaned = re.sub(r"\s+", " ", text).strip(" -–—|/")
    if not cleaned or len(cleaned) > 140:
        return False
    if len(re.findall(r"[।.!?]", cleaned)) > 1:
        return False
    if re.search(r"[0-9০-৯]", cleaned):
        return False

    normalized = normalize_text(cleaned)
    if any(suffix in normalized for suffix in NON_CONTRIBUTOR_TITLE_SUFFIXES):
        return False

    evidence = extract_contributor_evidence(cleaned, raw_value=cleaned)
    if evidence["contributors"]:
        return True

    author_candidates = evidence["authors"]
    if not author_candidates:
        return False

    if normalize_text(", ".join(author_candidates)) == normalized:
        return True

    return False


def split_display_title(display_title):
    cleaned = re.sub(r"\s+", " ", display_title).strip()
    if not cleaned:
        return "", ""

    matches = list(DISPLAY_TITLE_SEPARATOR_PATTERN.finditer(cleaned))
    for match in reversed(matches):
        title = cleaned[: match.start()].strip()
        author_line = cleaned[match.end() :].strip()
        if title and trailing_looks_like_contributor_phrase(author_line):
            return title, author_line
    return cleaned, ""


def parse_source_page_metadata(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    full_title = title_tag.get_text(" ", strip=True) if title_tag else ""
    title, title_author = split_display_title(full_title)

    author_line = ""
    meta_author_line = ""
    series = ""
    category = ""
    meta = soup.find("div", class_="entry-meta entry-meta-after-content")
    if meta:
        def read_terms(class_name):
            span = meta.find("span", class_=class_name)
            if span is None:
                return ""
            links = span.find_all("a")
            if links:
                return ", ".join(link.get_text(" ", strip=True) for link in links)
            return span.get_text(" ", strip=True)

        meta_author_line = read_terms("entry-terms-authors")
        author_line = meta_author_line or title_author
        series = read_terms("entry-terms-series")
        category = read_terms("entry-terms-ld_course_category")
    else:
        author_line = title_author

    canonical = soup.find("link", rel="canonical")
    canonical_url = canonical.get("href", "").strip() if canonical else ""
    normalized_url = normalize_source_url(canonical_url or source_url)
    if not full_title and not author_line and not series and not category:
        raise ValueError("The source page did not contain recognizable metadata.")

    raw_data = {
        "title": title,
        "display_title": full_title,
        "full_title": full_title,
        "author_line": author_line,
        "meta_author_line": meta_author_line,
        "title_author_line": title_author,
        "series": series,
        "category": category,
        "metadata_source": "book_page",
    }
    return metadata_entry_defaults(
        source_url=normalized_url,
        title=title or normalized_url.rstrip("/").split("/")[-1],
        author_line=author_line,
        raw_data=raw_data,
    )


def fetch_source_page_metadata(source_url, session=None):
    session = session or requests.Session()
    session.headers.update(SEARCH_HEADERS)
    normalized_url = normalize_source_url(source_url)
    response = get_with_host_fallback(session, normalized_url, timeout=30)
    response.raise_for_status()
    return parse_source_page_metadata(response.text, normalized_url)


def upsert_source_catalog_entry(metadata):
    defaults = dict(metadata)
    incoming_raw_data = defaults.get("raw_data") if isinstance(defaults.get("raw_data"), dict) else {}
    existing = SourceCatalogEntry.objects.filter(source_url=metadata["source_url"]).only("id", "raw_data").first()
    if existing is not None:
        defaults["raw_data"] = {
            **(existing.raw_data if isinstance(existing.raw_data, dict) else {}),
            **incoming_raw_data,
        }
    entry, _ = SourceCatalogEntry.objects.update_or_create(
        source_url=metadata["source_url"],
        defaults=defaults,
    )
    return entry
