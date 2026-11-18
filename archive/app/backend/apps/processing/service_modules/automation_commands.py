
def create_request_for_record(record, state=BookCreationRequestState.INITIAL, origin=SubmissionOrigin.CURATION):
    if (
        state == BookCreationRequestState.INITIAL
        and not can_process_record_url(record.url)
    ):
        logger.warning(
            "Skipping request creation for record %s because its URL is unsupported: %s",
            record.id,
            record.url,
        )
        return None
    processing_request = BookCreationRequest.objects.create(
        id=next_request_id(request_id_for_record(record)),
        book_record=record,
        state=state,
        origin=origin,
    )
    sync_record_state(record)
    domains = processing_domains_for_request_change(None, state, record=record)
    if origin == SubmissionOrigin.AUTOMATION:
        domains.update(
            {
                PROCESSING_CARD_CATALOG_AUTOMATION,
                PROCESSING_CARD_CREATE_OVERVIEW,
            }
        )
    publish_processing_ui_domains(domains)
    if state == BookCreationRequestState.INITIAL:
        processing_request = queue_processing_request(processing_request)
    return processing_request


def create_requests_for_record_ids(record_ids, *, actor=None, origin=SubmissionOrigin.CURATION):
    created = []
    for record in BookRecord.objects.filter(pk__in=record_ids).order_by("name", "id"):
        if not record_is_selectable(record):
            continue
        processing_request = create_request_for_record(record, origin=origin)
        if processing_request is not None:
            created.append(processing_request)
    return created


def update_automation_settings(kind, payload):
    automation_settings = get_automation_settings(kind)
    automation_settings.enabled = bool(payload.get("enabled", automation_settings.enabled))
    automation_settings.interval = str(payload.get("interval") or automation_settings.interval)
    raw_time = payload.get("time")
    if raw_time:
        if isinstance(raw_time, time_type):
            automation_settings.time = raw_time
        else:
            hours, minutes = str(raw_time).split(":", 1)
            automation_settings.time = time_type(int(hours), int(minutes))
    automation_settings.saved = True
    automation_settings.status_message = "Saved."
    if automation_settings.pk:
        automation_settings.save(update_fields=["enabled", "interval", "time", "saved", "status_message", "updated_at"])
    else:
        automation_settings.save()
    publish_processing_ui_domains(processing_domains_for_automation(kind))
    return automation_settings


def _local_scheduled_datetime(now, scheduled_time):
    local_now = timezone.localtime(now)
    return local_now.replace(
        hour=scheduled_time.hour,
        minute=scheduled_time.minute,
        second=0,
        microsecond=0,
    )


def automation_is_due(automation_settings, *, now=None):
    if not automation_settings.enabled:
        return False

    now = now or timezone.now()
    scheduled_at = _local_scheduled_datetime(now, automation_settings.time)
    local_now = timezone.localtime(now)
    if local_now < scheduled_at:
        return False

    last_run_at = automation_settings.last_run_at
    if last_run_at is None:
        return True

    last_local = timezone.localtime(last_run_at)
    days_since_last_run = (scheduled_at.date() - last_local.date()).days

    if automation_settings.interval == "daily":
        return last_local < scheduled_at
    if automation_settings.interval == "weekly":
        return days_since_last_run >= 7
    if automation_settings.interval == "biweekly":
        return days_since_last_run >= 14
    if automation_settings.interval == "monthly":
        return (
            scheduled_at.year,
            scheduled_at.month,
        ) != (
            last_local.year,
            last_local.month,
        )
    return days_since_last_run >= 7


def run_due_processing_automations(*, now=None):
    now = now or timezone.now()
    results = {}

    catalog_settings = get_automation_settings(ProcessingAutomationKind.CATALOG)
    if automation_is_due(catalog_settings, now=now):
        state = run_catalog_automation(trigger_source=SYNC_TRIGGER_SOURCE_SCHEDULER)
        results["catalog"] = {
            "ran": sync_run_mode(state) == SYNC_RUN_MODE_CATALOG_AUTOMATION,
            "status": state.status,
            "runMode": sync_run_mode(state),
        }
    else:
        results["catalog"] = {"ran": False, "status": "idle", "runMode": None}

    incomplete_settings = get_automation_settings(ProcessingAutomationKind.INCOMPLETE)
    if automation_is_due(incomplete_settings, now=now):
        state = run_incomplete_automation(trigger_source=SYNC_TRIGGER_SOURCE_SCHEDULER)
        results["incomplete"] = {
            "ran": sync_run_mode(state) == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            "status": state.status,
            "runMode": sync_run_mode(state),
        }
    else:
        results["incomplete"] = {"ran": False, "status": "idle", "runMode": None}

    return results


def run_manual_catalog_sync(
    remote_pages=None,
    *,
    trigger_source=SYNC_TRIGGER_SOURCE_BUTTON,
):
    sync_state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    if sync_owner_conflicts(sync_state, SYNC_RUN_MODE_MANUAL):
        return sync_state
    if (
        sync_state.status == ProcessingSyncStatus.PAUSED
        and catalog_sync_phase_status(sync_state) == CATALOG_PHASE_STATUS_PAUSED
    ):
        return resume_sync(
            PROCESSING_SYNC_KEY_CATALOG,
            run_mode=SYNC_RUN_MODE_MANUAL,
        )
    if sync_state.status in SYNC_ACTIVE_STATUSES:
        return sync_state
    return start_sync(
        remote_pages or None,
        run_mode=SYNC_RUN_MODE_MANUAL,
        sync_key=PROCESSING_SYNC_KEY_CATALOG,
        trigger_source=trigger_source,
    )


def run_catalog_automation(*, trigger_source=SYNC_TRIGGER_SOURCE_BUTTON):
    sync_state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    if sync_owner_conflicts(sync_state, SYNC_RUN_MODE_CATALOG_AUTOMATION):
        if trigger_source == SYNC_TRIGGER_SOURCE_SCHEDULER:
            update_automation_run_status(
                SYNC_RUN_MODE_CATALOG_AUTOMATION,
                "Waiting for the catalog runtime to become idle.",
            )
        return sync_state
    if catalog_request_creation_can_resume(sync_state) or (
        sync_state.status == ProcessingSyncStatus.PAUSED
        and catalog_sync_phase_status(sync_state) == CATALOG_PHASE_STATUS_PAUSED
    ):
        return resume_sync(
            PROCESSING_SYNC_KEY_CATALOG,
            run_mode=SYNC_RUN_MODE_CATALOG_AUTOMATION,
        )
    if sync_state.status in SYNC_ACTIVE_STATUSES:
        return sync_state
    if (
        catalog_sync_phase_status(sync_state) == CATALOG_PHASE_STATUS_COMPLETED
        and catalog_request_creation_phase_status(sync_state)
        == CATALOG_PHASE_STATUS_NOT_STARTED
    ):
        return begin_catalog_request_creation(sync_state)
    remote_pages = []
    if allow_processing_remote_page_payloads():
        remote_pages = catalog_remote_pages(sync_state.remote_pages)
    if settings.CELERY_TASK_ALWAYS_EAGER and not remote_pages:
        remote_pages = source_catalog_remote_pages()
    return start_sync(
        remote_pages or None,
        run_mode=SYNC_RUN_MODE_CATALOG_AUTOMATION,
        sync_key=PROCESSING_SYNC_KEY_CATALOG,
        trigger_source=trigger_source,
    )


def run_incomplete_automation(*, trigger_source=SYNC_TRIGGER_SOURCE_BUTTON):
    sync_state = get_sync_state(PROCESSING_SYNC_KEY_INCOMPLETE)
    if sync_state.status == ProcessingSyncStatus.PAUSED:
        return resume_sync(
            PROCESSING_SYNC_KEY_INCOMPLETE,
            run_mode=SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
        )
    if sync_state.status in SYNC_ACTIVE_STATUSES:
        return sync_state
    return start_sync(
        None,
        run_mode=SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
        sync_key=PROCESSING_SYNC_KEY_INCOMPLETE,
        trigger_source=trigger_source,
    )


def reset_processing_data(*, revoke_tasks=False, purge_queue=False):
    task_ids = collect_processing_task_ids() if revoke_tasks else set()
    if task_ids:
        revoke_processing_task_ids(task_ids)

    with transaction.atomic():
        BookCreationRequest.objects.all().delete()
        BookRecord.objects.update(
            book_creation_state=BookCreationState.NOT_CREATED,
            linked_book=None,
            is_duplicate=False,
            duplicate_of_record=None,
        )
        ProcessingSyncState.objects.all().update(
            status=ProcessingSyncStatus.IDLE,
            progress=None,
            remote_pages=[],
            page_index=0,
            fetched_count=0,
            skipped_count=0,
            updated_count=0,
            appended_count=0,
            message="Ready to sync.",
            task_id="",
            queue_name="",
            last_error="",
        )
        publish_processing_ui_domains(PROCESSING_CARD_KEYS)

    if purge_queue:
        purge_processing_task_queue()


PROCESSING_SOURCE_METADATA_CHECKPOINT = "source-metadata"
PROCESSING_SCRAPED_CONTENT_CHECKPOINT = "scraped-content"


def _request_progress(processing_request):
    return processing_request.progress if isinstance(processing_request.progress, dict) else {}
