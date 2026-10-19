import logging

import requests
from bs4 import BeautifulSoup
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.scraper_support.network import decode_html_response
from apps.ingestion.source_processing.transport import ControlledSourceSession
from apps.ingestion.source_workspace.queries import source_entries, source_snapshots
from apps.ingestion.source_workspace.update_probe import (
    cached_source_probe,
    source_update_probe,
)
from apps.processing.jobs.attempts import AttemptLost, checkpoint_attempt
from apps.processing.jobs.execution_errors import ExecutionFailure

from .queries import current_discovery_job
from .rebuilding import rebuild_updated_source

logger = logging.getLogger(__name__)


def published_source_probe(snapshot):
    stored = getattr(snapshot.entry, "source_update", None) or {}
    if stored.get("published_signature"):
        return {
            "signature": stored["published_signature"],
            "chapter_count": stored.get("published_chapter_count", 0),
        }
    if snapshot.book is None:
        return None
    jobs = snapshot.book.background_jobs.filter(
        kind="process_source", state="succeeded"
    ).order_by("-created_at")
    for job in jobs.only("checkpoint")[:1]:
        return cached_source_probe(job, snapshot.entry.source_url)
    return None


@transaction.atomic
def save_update_probe(entry, probe, baseline):
    current = SourceCatalogEntry.objects.select_for_update().get(pk=entry.pk)
    previous = current.raw_data.get("source_update", {})
    source_complete = current.raw_data.get("source_unfinished") is False and bool(
        current.raw_data.get("source_was_unfinished")
    )
    completion_pending = source_complete and previous.get(
        "published_completion"
    ) != current.raw_data.get("source_finished_at")
    value = {
        **previous,
        **probe,
        "checked_at": timezone.now().isoformat(),
        "status": "available"
        if completion_pending
        or baseline
        and baseline["signature"] != probe["signature"]
        else "current"
        if baseline
        else "unknown",
        "published_signature": baseline["signature"] if baseline else None,
        "published_chapter_count": baseline["chapter_count"] if baseline else None,
        "source_complete": source_complete,
    }
    current.raw_data = {**current.raw_data, "source_update": value}
    current.save(update_fields=["raw_data"])


@transaction.atomic
def save_published_probe(entry, probe):
    save_update_probe(entry, probe, probe)
    current = SourceCatalogEntry.objects.select_for_update().get(pk=entry.pk)
    current.raw_data["source_update"] = {
        **current.raw_data["source_update"],
        "status": "current",
        "published_completion": current.raw_data.get("source_finished_at"),
    }
    current.save(update_fields=["raw_data"])


def check_unfinished_updates(ownership):
    job = current_discovery_job(ownership.job_id)
    completed = job.checkpoint.get("update_checks", [])
    entries = source_entries({"q": "", "status": "linked"}).filter(
        Q(raw_data__source_unfinished=True) | Q(raw_data__source_was_unfinished=True)
    )
    snapshots = source_snapshots(
        list(entries.exclude(pk__in=completed)), job.requested_by
    )

    def boundary():
        current = current_discovery_job(job.pk)
        if not checkpoint_attempt(
            ownership, current.checkpoint, "checking_source_updates"
        ):
            raise AttemptLost("Source update checks stopped.")

    with ControlledSourceSession(boundary) as session:
        for snapshot in snapshots:
            if snapshot.book is None or snapshot.book.state != "published":
                continue
            boundary()
            try:
                response = session.get(snapshot.entry.source_url)
                response.raise_for_status()
                probe = source_update_probe(
                    BeautifulSoup(decode_html_response(response), "html.parser"),
                    snapshot.entry.source_url,
                )
                save_update_probe(
                    snapshot.entry, probe, published_source_probe(snapshot)
                )
            except (ExecutionFailure, requests.RequestException):
                logger.warning(
                    "Source update check could not complete.",
                    extra={"source_id": str(snapshot.entry.pk)},
                )
                continue
            outcome = rebuild_updated_source(ownership, snapshot)
            completed.append(str(snapshot.entry.pk))
            current = current_discovery_job(job.pk)
            if not checkpoint_attempt(
                ownership,
                {
                    **current.checkpoint,
                    "update_checks": completed,
                    "update_rebuilds": [
                        *current.checkpoint.get("update_rebuilds", []),
                        *([outcome] if outcome else []),
                    ],
                },
                "checking_source_updates",
            ):
                return False
    return True
