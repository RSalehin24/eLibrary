

def summarize_source_catalog_snapshots(snapshots):
    summary = empty_source_catalog_snapshot_summary()
    for snapshot in snapshots:
        update_source_catalog_snapshot_summary(summary, snapshot)
    return summary


def empty_source_catalog_snapshot_summary():
    return {
        "total": 0,
        "new": 0,
        "queued": 0,
        "processing": 0,
        "stopped": 0,
        "unfinished": 0,
        "failed": 0,
        "ready": 0,
        "deleted": 0,
    }


def update_source_catalog_snapshot_summary(summary, snapshot):
    summary["total"] += 1
    status = snapshot.get("curation_status")

    if status == "processing":
        latest_job_status = (snapshot.get("latest_job_status") or "").strip()
        latest_submission_status = (snapshot.get("latest_submission_status") or "").strip()
        if latest_job_status == JobStatus.QUEUED or latest_submission_status == "queued":
            summary["queued"] += 1
        else:
            summary["processing"] += 1
        return

    if status in summary:
        summary[status] += 1


def source_catalog_entry_snapshots(queryset):
    snapshots = [
        serialize_source_catalog_entry_inspection(inspection)
        for inspection in iter_source_catalog_entry_inspections(queryset)
    ]
    return snapshots, summarize_source_catalog_snapshots(snapshots)


def source_catalog_entry_overview(queryset, entry_statuses=None):
    selected_statuses = set(entry_statuses or OVERVIEW_CURATION_STATUSES)
    entries = []
    summary = empty_source_catalog_snapshot_summary()

    for inspection in iter_source_catalog_entry_inspections(queryset):
        snapshot = serialize_source_catalog_entry_inspection(inspection)
        update_source_catalog_snapshot_summary(summary, snapshot)
        if snapshot["curation_status"] in selected_statuses:
            entries.append(snapshot)

    return entries, summary


def build_catalog_curation_run_summary():
    return {
        "catalog_entries": 0,
        "refreshed_entries": 0,
        "queued_creates": 0,
        "queued_updates": 0,
        "skipped_ready": 0,
        "skipped_processing": 0,
        "skipped_deleted": 0,
        "errors": [],
        "status_counts": {
            "new": 0,
            "processing": 0,
            "stopped": 0,
            "unfinished": 0,
            "failed": 0,
            "ready": 0,
            "deleted": 0,
        },
    }


def should_update_existing_book(inspection, mode):
    status = inspection["curation_status"]
    if status in {"processing", "deleted"}:
        return False
    if mode == CatalogCurationMode.ALL:
        return inspection["local_book"] is not None
    return status in {"unfinished", "failed", "stopped"}


def should_create_missing_book(inspection):
    local_book = inspection["local_book"]
    return (local_book is None or bool(local_book.deleted_at)) and inspection[
        "curation_status"
    ] in {"new", "failed", "stopped", "deleted"}


def should_retry_failed_entry(inspection, now=None):
    if inspection["curation_status"] != "failed":
        return True

    now = now or timezone.now()
    activity_at = inspection.get("activity_at")
    if activity_at is None:
        return True

    return now - activity_at >= FAILED_AUTOMATION_RETRY_COOLDOWN


def submission_origin_for_run(run):
    if run.trigger == CatalogCurationTrigger.SCHEDULED:
        return SubmissionOrigin.AUTOMATION
    return SubmissionOrigin.CURATION
