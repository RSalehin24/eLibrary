from hashlib import sha256

from apps.ingestion.source_processing.page_cache import (
    ControlledSourceContext,
    SourcePageCache,
)
from apps.ingestion.source_processing.transport import ControlledSourceSession
from apps.processing.jobs.attempts import checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

from .parser import discovery_page
from .persistence import commit_discovery_page
from .queries import current_discovery_job


def discovery_checkpoint(job, cache, page):
    url, entries, next_url = page
    signatures = catalog_page_signatures(job.checkpoint, entries)
    visited = [*job.checkpoint.get("discovered_urls", []), url]
    if next_url in visited:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_catalog_pagination_loop")
    limited = len(visited) >= job.input["command"]["max_pages"]
    if limited and next_url and job.input["command"].get("fetch_all"):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_catalog_scan_limit")
    return {
        **cache.checkpoint,
        "discovered_urls": visited,
        "discovery_page_signatures": signatures,
        "discovered_pages": len(visited),
        "discovered_entries": job.checkpoint.get("discovered_entries", 0)
        + len(entries),
        "next_page_url": next_url,
        "discovery_complete": not next_url or limited,
        "more_pages_available": bool(next_url and limited),
    }


def catalog_page_signatures(checkpoint, entries):
    signatures = checkpoint.get("discovery_page_signatures", [])
    if not entries:
        if not checkpoint.get("discovered_entries") and not checkpoint.get(
            "unfinished_scan"
        ):
            raise ExecutionFailure(FailureKind.PERMANENT, "source_catalog_empty")
        return signatures
    signature = sha256(
        "\n".join(sorted(entry["source_url"] for entry in entries)).encode()
    ).hexdigest()
    if signature in signatures:
        raise ExecutionFailure(
            FailureKind.PERMANENT, "source_catalog_pagination_stalled"
        )
    return [*signatures, signature]


def visit_catalog_page(ownership, cache, page):
    url, soup = page
    entries, next_url = discovery_page(soup, url)
    job = current_discovery_job(ownership.job_id)
    if job.input["command"].get("catalog_scope") == "unfinished":
        job.checkpoint = {**job.checkpoint, "unfinished_scan": str(job.pk)}
        entries = [
            {
                **entry,
                "raw_data": {
                    **entry.get("raw_data", {}),
                    "source_unfinished": True,
                    "unfinished_scan": str(job.pk),
                },
            }
            for entry in entries
        ]
    checkpoint = discovery_checkpoint(job, cache, (url, entries, next_url))
    if not commit_discovery_page(ownership, entries, checkpoint):
        return None
    cache.checkpoint = checkpoint
    return None if checkpoint["discovery_complete"] else next_url


def collect_catalog(ownership, job):
    cache = SourcePageCache(ownership, job.checkpoint, current_discovery_job)
    url = job.checkpoint.get("next_page_url", job.input["command"]["catalog_url"])
    with ControlledSourceSession(cache.boundary) as session:
        context = ControlledSourceContext(session, cache)
        while url:
            soup = context.fetch_soup(url, kind="catalog")
            url = visit_catalog_page(ownership, cache, (url, soup))
    job = current_discovery_job(job.pk)
    return checkpoint_attempt(ownership, job.checkpoint, "source_catalog_discovered")


def run_source_discovery(ownership):
    from apps.processing.automations.processing import dispatch_automation_sources

    job = current_discovery_job(ownership.job_id)
    if job.checkpoint.get("discovery_complete"):
        completed = checkpoint_attempt(
            ownership, job.checkpoint, "source_catalog_discovered"
        )
    else:
        try:
            completed = collect_catalog(ownership, job)
        except OSError:
            raise ExecutionFailure(
                FailureKind.TRANSIENT, "source_storage_unavailable"
            ) from None
    return completed and dispatch_automation_sources(ownership)
