

def get_sync_state(sync_key=PROCESSING_SYNC_KEY_CATALOG):
    state = ProcessingSyncState.objects.filter(singleton_key=sync_key).first()
    if state is None:
        state = ProcessingSyncState(
            singleton_key=sync_key,
            message="Ready to sync.",
        )
    return state


def active_sync_scope(default=PROCESSING_SYNC_KEY_CATALOG):
    incomplete_state = get_sync_state(PROCESSING_SYNC_KEY_INCOMPLETE)
    if incomplete_state.status in {
        ProcessingSyncStatus.SYNCING,
        ProcessingSyncStatus.PAUSING,
        ProcessingSyncStatus.PAUSED,
    }:
        return PROCESSING_SYNC_KEY_INCOMPLETE

    catalog_state = get_sync_state(PROCESSING_SYNC_KEY_CATALOG)
    if catalog_state.status in {
        ProcessingSyncStatus.SYNCING,
        ProcessingSyncStatus.PAUSING,
        ProcessingSyncStatus.PAUSED,
    }:
        return PROCESSING_SYNC_KEY_CATALOG

    return default


def sync_is_active_or_paused(state):
    return state.status in {
        ProcessingSyncStatus.SYNCING,
        ProcessingSyncStatus.PAUSING,
        ProcessingSyncStatus.PAUSED,
    }


def sync_owner_conflicts(state, run_mode):
    if state.status in SYNC_ACTIVE_STATUSES:
        return sync_run_mode(state) != run_mode
    if state.status != ProcessingSyncStatus.PAUSED:
        return False
    if (
        state.singleton_key == PROCESSING_SYNC_KEY_CATALOG
        and catalog_shared_runtime(sync_run_mode(state))
        and catalog_shared_runtime(run_mode)
    ):
        return False
    return sync_run_mode(state) != run_mode


def serialize_sync_state(state, *, include_remote_pages=True):
    progress = (
        sync_progress_payload(state)
        if isinstance(state.progress, dict)
        else None
    )
    payload = {
        "status": state.status,
        "progress": progress,
        "phase": sync_phase(state),
        "fetchedCount": state.fetched_count,
        "skippedCount": state.skipped_count,
        "updatedCount": state.updated_count,
        "appendedCount": state.appended_count,
        "message": state.message,
        "pageIndex": state.page_index,
        "runMode": sync_run_mode(state),
        "triggerSource": sync_trigger_source(state),
        "scope": state.singleton_key,
        "workerManaged": bool(state.task_id),
    }
    if include_remote_pages:
        payload["remotePages"] = state.remote_pages
    return payload


def serialize_automation_settings(automation_settings):
    return {
        "kind": automation_settings.kind,
        "enabled": automation_settings.enabled,
        "interval": automation_settings.interval,
        "time": automation_settings.time.strftime("%H:%M"),
        "saved": automation_settings.saved,
        "lastRunAt": (
            automation_settings.last_run_at.isoformat()
            if automation_settings.last_run_at
            else None
        ),
        "statusMessage": automation_settings.status_message,
    }


def persisted_sync_status(state):
    latest_status = (
        ProcessingSyncState.objects.filter(pk=state.pk)
        .values_list("status", flat=True)
        .first()
    )
    return latest_status or state.status


def normalize_automation_settings(automation_settings, *, persist=False):
    update_fields = []

    if not automation_settings.saved:
        if automation_settings.interval != DEFAULT_AUTOMATION_INTERVAL:
            automation_settings.interval = DEFAULT_AUTOMATION_INTERVAL
            update_fields.append("interval")
        if automation_settings.time != DEFAULT_AUTOMATION_TIME:
            automation_settings.time = DEFAULT_AUTOMATION_TIME
            update_fields.append("time")

    if automation_settings.status_message == LEGACY_AUTOMATION_STATUS_MESSAGE:
        automation_settings.status_message = ""
        update_fields.append("status_message")

    if update_fields and persist and automation_settings.pk:
        automation_settings.save(update_fields=[*update_fields, "updated_at"])

    return automation_settings


def get_automation_settings(kind):
    automation_settings = ProcessingAutomationSettings.objects.filter(kind=kind).first()
    if automation_settings is None:
        automation_settings = ProcessingAutomationSettings(
            kind=kind,
            enabled=False,
            interval=DEFAULT_AUTOMATION_INTERVAL,
            time=DEFAULT_AUTOMATION_TIME,
            saved=False,
            status_message="",
        )
    return normalize_automation_settings(automation_settings)


def processing_request_card_for_state(state):
    for card_id, states in PROCESSING_REQUEST_CARD_STATES.items():
        if state in states:
            return card_id
    return None


def processing_overview_card_for_state(state):
    if state in PROCESSING_STATE_REQUEST_GROUP:
        return PROCESSING_CARD_CREATE_OVERVIEW
    if state in PROCESSING_STATE_ON_HOLD_GROUP:
        return PROCESSING_CARD_ON_HOLD_OVERVIEW
    return None


def processing_record_is_incomplete(record_or_snapshot):
    if record_or_snapshot is None:
        return False
    if isinstance(record_or_snapshot, dict):
        category = record_or_snapshot.get("category")
        was_incomplete = bool(record_or_snapshot.get("was_incomplete"))
    else:
        category = getattr(record_or_snapshot, "category", "")
        was_incomplete = bool(getattr(record_or_snapshot, "was_incomplete", False))
    return was_incomplete or category_is_incomplete(category)


def processing_record_snapshot(record):
    if record is None:
        return None
    return {
        "id": str(record.id),
        "category": record.category,
        "was_incomplete": bool(record.was_incomplete),
        "resolved_from_incomplete": bool(record.resolved_from_incomplete),
        "book_creation_state": record.book_creation_state,
        "linked_book_id": str(record.linked_book_id) if record.linked_book_id else "",
        "is_duplicate": bool(record.is_duplicate),
        "duplicate_of_record_id": (
            str(record.duplicate_of_record_id) if record.duplicate_of_record_id else ""
        ),
    }


def processing_request_snapshot(processing_request):
    if processing_request is None:
        return None
    return {
        "id": str(processing_request.id),
        "state": processing_request.state,
        "book_record_id": str(processing_request.book_record_id),
        "linked_book_id": (
            str(processing_request.linked_book_id)
            if processing_request.linked_book_id
            else ""
        ),
        "duplicate_of_request_id": (
            str(processing_request.duplicate_of_request_id)
            if processing_request.duplicate_of_request_id
            else ""
        ),
        "duplicate_of_record_id": (
            str(processing_request.duplicate_of_record_id)
            if processing_request.duplicate_of_record_id
            else ""
        ),
        "duplicate_confirmed": bool(processing_request.duplicate_confirmed),
        "is_resumed": bool(processing_request.is_resumed),
        "is_confirmed_not_duplicate": bool(processing_request.is_confirmed_not_duplicate),
    }


def default_sync_state_payload(scope):
    return {
        "status": ProcessingSyncStatus.IDLE,
        "progress": None,
        "phase": CATALOG_SYNC_PHASE,
        "fetchedCount": 0,
        "skippedCount": 0,
        "updatedCount": 0,
        "appendedCount": 0,
        "message": "Ready to sync.",
        "pageIndex": 0,
        "runMode": SYNC_RUN_MODE_MANUAL,
        "triggerSource": SYNC_TRIGGER_SOURCE_BUTTON,
        "scope": scope,
        "workerManaged": False,
        "remotePages": [],
    }


def default_automation_payload(kind):
    return {
        "kind": kind,
        "enabled": False,
        "interval": DEFAULT_AUTOMATION_INTERVAL,
        "time": DEFAULT_AUTOMATION_TIME.strftime("%H:%M"),
        "saved": False,
        "lastRunAt": None,
        "statusMessage": "",
    }
