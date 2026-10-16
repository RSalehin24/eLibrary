from copy import deepcopy
from typing import Any

from bs4 import BeautifulSoup

from apps.ingestion.pipeline.scraper_support.network import decode_html_response
from apps.processing.jobs.attempts import AttemptLost, checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .policy import (
    MAX_CHECKPOINT_BYTES,
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

    def boundary(self):
        self.authority(self.ownership.job_id)
        if not checkpoint_attempt(self.ownership, self.checkpoint, "fetching_source"):
            raise AttemptLost("The source operation was stopped.")

    def read(self, url):
        require_source_url(url, self.allowed_hosts)
        self.boundary()
        reference = self.pages.get(url)
        return read_artifact(self.ownership.job_id, reference) if reference else None

    def save(self, url, html):
        require_source_url(url, self.allowed_hosts)
        self.size += len(html.encode())
        if self.size > MAX_CHECKPOINT_BYTES or len(self.pages) >= MAX_SOURCE_PAGES:
            raise ExecutionFailure(FailureKind.PERMANENT, "source_checkpoint_limit")
        self.pages[url] = write_artifact(self.ownership.job_id, html)
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
        response = self.session.get(url)
        if response.status_code >= 400:
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
