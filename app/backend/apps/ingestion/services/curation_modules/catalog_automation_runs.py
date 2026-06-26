

def process_catalog_curation_run(run_id, retry_count=0, task_id=""):
    run = CatalogCurationRun.objects.select_related("requested_by").get(pk=run_id)
    if run.status == JobStatus.CANCELLED:
        return run
    if run.cancel_requested:
        return finalize_cancelled_catalog_curation_run(run)
    run.status = JobStatus.PROCESSING
    run.retry_count = retry_count
    run.task_id = task_id or run.task_id
    run.started_at = timezone.now()
    run.last_error = ""
    run.save(update_fields=["status", "retry_count", "task_id", "started_at", "last_error", "updated_at"])

    summary = build_catalog_curation_run_summary()

    try:
        run.refresh_from_db(fields=["status", "cancel_requested", "updated_at"])
        if run.status == JobStatus.CANCELLED or run.cancel_requested:
            return finalize_cancelled_catalog_curation_run(run)
        if run.refresh_catalog:
            result = refresh_catalog_parallel()
            summary["refreshed_entries"] = result["total"]

        entry_queryset = SourceCatalogEntry.objects.order_by("title")
        summary["catalog_entries"] = entry_queryset.count()
        submission_origin = submission_origin_for_run(run)

        for inspection in iter_source_catalog_entry_inspections(entry_queryset):
            run.refresh_from_db(fields=["status", "cancel_requested", "updated_at"])
            if run.status == JobStatus.CANCELLED or run.cancel_requested:
                run.summary = summary
                run.save(update_fields=["summary", "updated_at"])
                return finalize_cancelled_catalog_curation_run(run)

            entry = inspection["entry"]
            status = inspection["curation_status"]
            summary["status_counts"][status] += 1

            if not should_retry_failed_entry(inspection):
                summary["skipped_processing"] += 1
                continue

            try:
                if should_create_missing_book(inspection):
                    create_submission_records(submitter=run.requested_by, parsed_entries=[{"kind": "url", "value": entry.source_url}], auto_process=True, origin=submission_origin)
                    summary["queued_creates"] += 1
                    continue
                if should_update_existing_book(inspection, run.mode):
                    _, created = queue_reprocess_book(inspection["local_book"], actor=run.requested_by, origin=submission_origin)
                    summary["queued_updates"] += 1 if created else 0
                    summary["skipped_processing"] += 0 if created else 1
                    continue
                summary["skipped_processing" if status == "processing" else "skipped_ready"] += 1
            except Exception as exc:
                if len(summary["errors"]) < 20:
                    summary["errors"].append({"source_url": entry.source_url, "error": str(exc)})

        run.summary = summary
        run.status = JobStatus.SUCCEEDED
        run.finished_at = timezone.now()
        run.save(update_fields=["summary", "status", "finished_at", "updated_at"])
        return run
    except Exception as exc:
        logger.exception("Catalog curation run failed", extra={"run_id": str(run.id)})
        run.summary = summary
        run.status = JobStatus.FAILED
        run.last_error = str(exc)
        run.finished_at = timezone.now()
        run.save(update_fields=["summary", "status", "last_error", "finished_at", "updated_at"])
        raise


def run_due_catalog_automation(now=None):
    settings_obj = get_catalog_automation_settings()
    if not settings_obj.enabled:
        return {"ran": False, "reason": "disabled"}

    now = timezone.localtime(now or timezone.now())
    latest_run = latest_catalog_automation_run()
    next_due_at = next_catalog_automation_due_at(settings_obj, now=now, latest_run=latest_run)
    settings_updated_at = timezone.localtime(settings_obj.updated_at or settings_obj.created_at)
    latest_run_at = timezone.localtime(latest_run.created_at) if latest_run else None

    if now < next_due_at:
        if latest_run_at and latest_run_at >= settings_updated_at:
            return {"ran": False, "reason": "already_ran"}
        return {"ran": False, "reason": "not_due"}

    if CatalogCurationRun.objects.filter(status__in=ACTIVE_RUN_STATUSES).exists():
        return {"ran": False, "reason": "busy"}

    run = create_catalog_curation_run(
        mode=settings_obj.mode,
        trigger=CatalogCurationTrigger.SCHEDULED,
        requested_by=None,
        refresh_catalog=True,
        refresh_max_pages=settings_obj.refresh_max_pages,
    )
    return {"ran": True, "run_id": str(run.id)}
