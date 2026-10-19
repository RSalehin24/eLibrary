from copy import deepcopy
from time import monotonic
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from apps.ingestion.pipeline.scraper_support.network import decode_html_response
from apps.processing.jobs.attempts import AttemptLost, checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .continuations import CollectionYield
from .editions import backfill_cached_pages, record_source_page
from .host_health import record_host_response, require_healthy_host, retry_after
from .policy import (
    MAX_SOURCE_CACHE_BYTES,
    MAX_SOURCE_PAGES,
    require_source_url,
    source_hosts,
)
from .queries import current_source_job
from .storage import read_artifact, write_artifact


class SourcePageCache:
    def __init__(self, ownership, checkpoint, authority=current_source_job):
        self.ownership = ownership
        self.checkpoint = deepcopy(checkpoint)
        reference = checkpoint.get("page_cache_ref")
        self.pages = read_artifact(ownership.job_id, reference) if reference else {}
        self.allowed_hosts = source_hosts()
        self.size = checkpoint.get("cache_bytes", 0)
        self.authority = authority
        if self.pages:
            backfill_cached_pages(ownership.job_id, self.pages)
        self.slice_started = monotonic()
        self.slice_pages = 0

    def boundary(self):
        self.authority(self.ownership.job_id)
        if not checkpoint_attempt(self.ownership, self.checkpoint, "fetching_source"):
            raise AttemptLost("The source operation was stopped.")

    def read(self, url):
        require_source_url(url, self.allowed_hosts)
        self.boundary()
        reference = self.pages.get(url)
        if (
            not reference
            and self.slice_pages
            and (self.slice_pages >= 10 or monotonic() - self.slice_started >= 30)
        ):
            raise CollectionYield("Continue collection from its saved pages.")
        return read_artifact(self.ownership.job_id, reference) if reference else None

    def save(self, url, html):
        require_source_url(url, self.allowed_hosts)
        previous = self.pages.get(url)
        previous_size = (
            len(read_artifact(self.ownership.job_id, previous).encode())
            if previous
            else 0
        )
        size = self.size - previous_size + len(html.encode())
        if size > MAX_SOURCE_CACHE_BYTES or (
            not previous and len(self.pages) >= MAX_SOURCE_PAGES
        ):
            raise ExecutionFailure(FailureKind.PERMANENT, "source_checkpoint_limit")
        self.pages[url] = write_artifact(self.ownership.job_id, html)
        self.size = size
        self.slice_pages += 1
        record_source_page(self.ownership.job_id, (url, html), self.pages[url])
        self.checkpoint = {
            **self.checkpoint,
            "page_cache_ref": write_artifact(self.ownership.job_id, self.pages),
            "pages_fetched": len(self.pages),
            "cache_bytes": self.size,
        }
        self.boundary()


class ControlledSourceContext:
    def __init__(self, session, cache: SourcePageCache):
        self.session = session
        self.cache = cache
        self.pages: list[dict[str, Any]] = []

    def fetch_html(self, url):
        cached = self.cache.read(url)
        if cached is not None:
            return cached
        host = urlsplit(url).hostname
        require_healthy_host(host)
        try:
            response = self.session.get(url)
        except ExecutionFailure:
            record_host_response(host, 503)
            raise
        record_host_response(host, response.status_code)
        if response.status_code >= 400:
            next_attempt = retry_after(response.headers.get("Retry-After"))
            if next_attempt:
                self.cache.checkpoint["source_retry_after"] = next_attempt.isoformat()
                self.cache.boundary()
            if response.status_code in {401, 403, 404}:
                code = (
                    "source_missing"
                    if response.status_code == 404
                    else "source_access_unavailable"
                )
                response.close()
                raise ExecutionFailure(FailureKind.TRANSIENT, code)
            kind = (
                FailureKind.TRANSIENT
                if response.status_code in {408, 429} or response.status_code >= 500
                else FailureKind.PERMANENT
            )
            raise ExecutionFailure(kind, "source_request_rejected")
        html = decode_html_response(response)
        self.cache.save(url, html)
        return html

    def fetch_soup(self, url, **labels):
        html = self.fetch_html(url)
        self.pages.append(
            {
                "url": url,
                "kind": labels.get("kind", "content"),
                "title": labels.get("title", ""),
                "status": "fetched",
                "status_code": 200,
            }
        )
        return BeautifulSoup(html, "html.parser")
