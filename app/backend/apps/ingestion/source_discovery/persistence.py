from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.jobs.attempts import checkpoint_attempt, owned_job

from .queries import current_discovery_job

CATALOG_FIELDS = ("title", "author_line", "normalized_title", "normalized_display")


def apply_discovered_values(entry, values):
    for field in CATALOG_FIELDS:
        setattr(entry, field, values[field])


def update_discovered_records(entries):
    existing = {
        entry.source_url: entry
        for entry in SourceCatalogEntry.objects.select_for_update()
        .filter(source_url__in=[entry["source_url"] for entry in entries])
        .only("source_url", *CATALOG_FIELDS)
        .order_by("pk")
    }
    now, changed, unchanged, new = timezone.now(), [], [], []
    for values in entries:
        entry = existing.get(values["source_url"])
        if entry is None:
            new.append(SourceCatalogEntry(**values))
        elif any(getattr(entry, field) != values[field] for field in CATALOG_FIELDS):
            apply_discovered_values(entry, values)
            entry.updated_at = entry.last_seen_at = now
            changed.append(entry)
        else:
            unchanged.append(entry.pk)
    SourceCatalogEntry.objects.bulk_create(new, ignore_conflicts=True)
    SourceCatalogEntry.objects.bulk_update(
        changed, [*CATALOG_FIELDS, "updated_at", "last_seen_at"]
    )
    SourceCatalogEntry.objects.filter(pk__in=unchanged).update(last_seen_at=now)


@transaction.atomic
def commit_discovery_page(ownership, entries, checkpoint):
    snapshot = current_discovery_job(ownership.job_id)
    User.objects.select_for_update(no_key=True).get(pk=snapshot.requested_by_id)
    job = owned_job(ownership)
    current_discovery_job(job.pk)
    if not checkpoint_attempt(ownership, job.checkpoint, "saving_source_catalog"):
        return False
    update_discovered_records(entries)
    return checkpoint_attempt(ownership, checkpoint, "source_catalog_page_saved")
