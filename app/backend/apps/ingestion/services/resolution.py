import logging
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.scraper_support.network import _get_allowed_source_hosts
from apps.ingestion.pipeline.scraper_support.text import normalize_text, texts_are_similar
from apps.ingestion.services.resolution_support import (
    ARCHIVE_MAX_PAGES,
    SEARCH_HEADERS,
    fetch_source_page_metadata,
    get_catalog_url,
    get_via_direct_ip_https as support_get_via_direct_ip_https,
    is_name_resolution_failure,
    metadata_entry_defaults,
    replace_url_host,
    resolve_host_with_dns_fallback as support_resolve_host_with_dns_fallback,
    source_request_hosts,
    split_display_title,
    upsert_source_catalog_entry,
)


logger = logging.getLogger(__name__)
CATALOG_URL = get_catalog_url()


def resolve_host_with_dns_fallback(host): return support_resolve_host_with_dns_fallback(host)


def get_via_direct_ip_https(session, url, host, ip, **kwargs): return support_get_via_direct_ip_https(session, url, host, ip, **kwargs)


def get_with_host_fallback(session, url, **kwargs):
    parsed = urlparse(url)
    candidate_hosts = source_request_hosts(parsed.netloc)
    candidate_urls = [replace_url_host(url, host) for host in candidate_hosts]
    fallback_errors = []

    for candidate_url in candidate_urls:
        try:
            return session.get(candidate_url, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            if not is_name_resolution_failure(exc):
                raise
            fallback_errors.append(exc)

    direct_ip_errors = []
    for host in candidate_hosts:
        candidate_url = replace_url_host(url, host)
        for resolved_ip in resolve_host_with_dns_fallback(host):
            try:
                return get_via_direct_ip_https(
                    session,
                    candidate_url,
                    host,
                    resolved_ip,
                    **kwargs,
                )
            except requests.exceptions.RequestException as exc:
                direct_ip_errors.append(exc)

    if direct_ip_errors:
        raise direct_ip_errors[-1]
    if fallback_errors:
        raise fallback_errors[-1]
    return session.get(url, **kwargs)


@dataclass
class ResolutionResult:
    status: str
    confidence: float
    resolved_url: str
    candidates: list
    raw: dict


class TitleResolver:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update(SEARCH_HEADERS)

    def refresh_catalog(self, max_pages=1, bucket=""):
        refreshed = []
        seen = set()
        page_signatures = set()
        page_number = 1
        while max_pages is None or page_number <= max_pages:
            response = get_with_host_fallback(
                self.session,
                get_catalog_url(),
                params=self.archive_query_params(page_number=page_number, bucket=bucket),
                timeout=30,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            page_entries = self.parse_catalog_page(soup)
            if not page_entries:
                break

            signature = tuple(entry["source_url"] for entry in page_entries[:5])
            if signature in page_signatures:
                break
            page_signatures.add(signature)

            for entry in page_entries:
                if entry["source_url"] in seen:
                    continue
                seen.add(entry["source_url"])
                _, created = SourceCatalogEntry.objects.update_or_create(
                    source_url=entry["source_url"],
                    defaults=entry,
                )
                if created:
                    refreshed.append(entry)
            page_number += 1

        return refreshed

    def archive_query_params(self, page_number=1, bucket=""):
        params = {}
        if bucket:
            params["_a_z"] = bucket
        if page_number > 1:
            params["_paged"] = page_number
        return params

    def derive_bucket(self, query):
        for char in query.strip():
            if char.isalnum() or "\u0980" <= char <= "\u09ff":
                return char.upper() if char.isascii() else char
        return ""

    def score_candidate_fields(self, query, normalized_query, title, author_line=""):
        normalized_title = normalize_text(title)
        normalized_display = normalize_text(f"{title} {author_line}")
        if normalized_title == normalized_query or normalized_display == normalized_query:
            return 1.0
        if texts_are_similar(query, title):
            return 0.88
        if normalized_query and (
            normalized_query in normalized_title or normalized_title in normalized_query
        ):
            return 0.78

        query_tokens = set(normalized_query.split())
        candidate_tokens = set(normalized_display.split())
        if query_tokens and candidate_tokens:
            overlap = len(query_tokens & candidate_tokens) / len(query_tokens | candidate_tokens)
            return round(overlap * 0.75, 3)
        return 0.0

    def parse_catalog_page(self, soup):
        entries = []
        seen = set()
        for result in soup.select(".facetwp-template .fwpl-result"):
            text_anchor = result.select_one(".fwpl-item.el-97dha a[href]")
            anchor = text_anchor or result.select_one("a[href]")
            if anchor is None:
                continue

            href = urljoin(get_catalog_url(), anchor["href"])
            parsed = urlparse(href)
            if parsed.netloc.lower() not in _get_allowed_source_hosts():
                continue
            if not parsed.path.startswith("/books/"):
                continue

            display_title = anchor.get_text(" ", strip=True)
            if not display_title or href in seen:
                continue

            seen.add(href)
            title, author_line = split_display_title(display_title)
            entries.append(
                metadata_entry_defaults(
                    source_url=href.rstrip("/") + "/",
                    title=title,
                    author_line=author_line,
                    raw_data={
                        "title": title,
                        "display_title": display_title,
                        "author_line": author_line,
                        "metadata_source": "archive_page",
                    },
                )
            )
        return entries

    def score_entry(self, query, normalized_query, entry):
        return self.score_candidate_fields(query, normalized_query, entry.title, entry.author_line)

    def collect_candidates(self, query, normalized_query):
        candidates = []
        for entry in SourceCatalogEntry.objects.all():
            confidence = self.score_entry(query, normalized_query, entry)
            if confidence <= 0:
                continue
            candidates.append(
                {
                    "title": entry.title,
                    "author": entry.author_line,
                    "url": entry.source_url,
                    "confidence": confidence,
                }
            )

        candidates.sort(key=lambda item: item["confidence"], reverse=True)
        return candidates[:3]

    def enrich_candidates_with_source_metadata(self, query, normalized_query, candidates):
        enriched_candidates = []
        for candidate in candidates:
            next_candidate = dict(candidate)
            try:
                metadata = fetch_source_page_metadata(candidate["url"], session=self.session)
                upsert_source_catalog_entry(metadata)
                next_candidate["title"] = metadata["title"]
                next_candidate["author"] = metadata["author_line"]
                next_candidate["confidence"] = max(
                    candidate["confidence"],
                    self.score_candidate_fields(
                        query,
                        normalized_query,
                        metadata["title"],
                        metadata["author_line"],
                    ),
                )
            except Exception:
                pass
            enriched_candidates.append(next_candidate)

        enriched_candidates.sort(key=lambda item: item["confidence"], reverse=True)
        return enriched_candidates[:3]

    def resolve(self, query, refresh_catalog=False):
        normalized_query = normalize_text(query)
        top_candidates = self.collect_candidates(query, normalized_query)
        refresh_error = ""

        should_refresh = refresh_catalog or not top_candidates
        if should_refresh:
            bucket = self.derive_bucket(query)
            try:
                self.refresh_catalog(
                    max_pages=ARCHIVE_MAX_PAGES,
                    bucket=bucket,
                )
            except Exception as exc:
                refresh_error = str(exc)
                logger.warning(
                    "Source catalog refresh failed during title resolution.",
                    exc_info=True,
                )
            top_candidates = self.collect_candidates(query, normalized_query)

        if top_candidates:
            top_candidates = self.enrich_candidates_with_source_metadata(
                query,
                normalized_query,
                top_candidates,
            )

        if top_candidates:
            top = top_candidates[0]
            second = top_candidates[1] if len(top_candidates) > 1 else None
            if top["confidence"] == 1.0 and (second is None or second["confidence"] < 1.0):
                return ResolutionResult(
                    status="exact_match",
                    confidence=top["confidence"],
                    resolved_url=top["url"],
                    candidates=top_candidates,
                    raw={"query": query, "refresh_error": refresh_error},
                )

        if top_candidates:
            return ResolutionResult(
                status="ambiguous",
                confidence=top_candidates[0]["confidence"],
                resolved_url="",
                candidates=top_candidates,
                raw={"query": query, "refresh_error": refresh_error},
            )

        return ResolutionResult(
            status="unresolved",
            confidence=0.0,
            resolved_url="",
            candidates=[],
            raw={"query": query, "refresh_error": refresh_error},
        )
