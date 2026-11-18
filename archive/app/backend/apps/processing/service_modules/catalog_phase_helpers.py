PROCESSING_CHECKPOINT_REDIS = {
    "url": "",
    "client": None,
    "disabled": False,
}


def normalize_category_key(value):
    return str(value or "").strip().casefold()


def category_is_incomplete(value):
    normalized = normalize_category_key(value)
    return any(keyword in normalized for keyword in INCOMPLETE_CATEGORY_KEYWORDS)


def incomplete_category_query(field_name="category"):
    query = Q()
    for keyword in INCOMPLETE_CATEGORY_KEYWORDS:
        query |= Q(**{f"{field_name}__icontains": keyword})
    return query


def catalog_phase_statuses(
    *,
    sync_status=CATALOG_PHASE_STATUS_NOT_STARTED,
    request_creation_status=CATALOG_PHASE_STATUS_NOT_STARTED,
):
    sync_status = catalog_phase_summary_status(sync_status)
    request_creation_status = catalog_phase_summary_status(request_creation_status)
    return {
        CATALOG_SYNC_PHASE: sync_status,
        CATALOG_REQUEST_CREATION_PHASE: request_creation_status,
    }


def _phase_saved_data(value):
    return value if isinstance(value, dict) else {}


def _phase_request_creation(value):
    return value if isinstance(value, dict) else None


def catalog_phase_is_active_status(status):
    return status in {
        CATALOG_PHASE_STATUS_RUNNING,
        CATALOG_PHASE_STATUS_PAUSING,
    }


def catalog_phase_summary_status(status):
    normalized_status = (
        status if status in CATALOG_PHASE_STATUSES else CATALOG_PHASE_STATUS_NOT_STARTED
    )
    if normalized_status == CATALOG_PHASE_STATUS_PAUSING:
        return CATALOG_PHASE_STATUS_RUNNING
    return normalized_status


def _runtime_catalog_phase_status(runtime_status, phase, progress_phase):
    if phase != progress_phase:
        return ""
    if runtime_status == ProcessingSyncStatus.PAUSING:
        return CATALOG_PHASE_STATUS_PAUSING
    if runtime_status == ProcessingSyncStatus.PAUSED:
        return CATALOG_PHASE_STATUS_PAUSED
    if runtime_status == ProcessingSyncStatus.SYNCING:
        return CATALOG_PHASE_STATUS_RUNNING
    return ""


def _catalog_phase_status_from_runtime(status, runtime_status, phase, progress_phase):
    runtime_phase_status = _runtime_catalog_phase_status(
        runtime_status,
        phase,
        progress_phase,
    )
    if runtime_phase_status:
        return runtime_phase_status
    return status


def _catalog_request_creation_checkpoint_available(
    request_creation,
    request_creation_base_token,
    request_creation_checkpoint="",
):
    return bool(
        _phase_request_creation(request_creation)
        or str(request_creation_base_token or "").strip()
        or str(request_creation_checkpoint or "").strip()
    )


def _normalize_catalog_phase_status_pair(
    sync_status,
    request_creation_status,
    *,
    progress_phase,
    request_creation,
    request_creation_base_token="",
    request_creation_checkpoint="",
):
    if (
        request_creation_status != CATALOG_PHASE_STATUS_NOT_STARTED
        and sync_status == CATALOG_PHASE_STATUS_NOT_STARTED
    ):
        sync_status = CATALOG_PHASE_STATUS_COMPLETED

    if not (
        catalog_phase_is_active_status(sync_status)
        and catalog_phase_is_active_status(request_creation_status)
    ):
        return sync_status, request_creation_status

    active_phase = (
        progress_phase
        if progress_phase in {CATALOG_SYNC_PHASE, CATALOG_REQUEST_CREATION_PHASE}
        else CATALOG_SYNC_PHASE
    )
    if active_phase == CATALOG_REQUEST_CREATION_PHASE:
        return CATALOG_PHASE_STATUS_COMPLETED, request_creation_status
    return (
        sync_status,
        (
            CATALOG_PHASE_STATUS_PAUSED
            if _catalog_request_creation_checkpoint_available(
                request_creation,
                request_creation_base_token,
                request_creation_checkpoint,
            )
            else CATALOG_PHASE_STATUS_NOT_STARTED
        ),
    )


def _catalog_phase_checkpoint_from_saved_data(saved_data):
    session_id = str(saved_data.get("sessionId") or "").strip()
    if not session_id:
        return ""
    return str(saved_data.get("checkpointToken") or "").strip() or catalog_sync_checkpoint_token(
        session_id,
        next_page_index=saved_data.get("nextPageIndex") or 0,
        fetched_count=saved_data.get("fetchedCount") or 0,
        live_fetch=bool(saved_data.get("liveFetch")),
    )


def _catalog_phase_state(
    phase,
    *,
    status=CATALOG_PHASE_STATUS_NOT_STARTED,
    owner="",
    trigger_source=SYNC_TRIGGER_SOURCE_BUTTON,
    checkpoint="",
    saved_at="",
    saved_data=None,
    request_creation=None,
    base_sync_checkpoint_token="",
):
    payload = {
        "status": status if status in CATALOG_PHASE_STATUSES else CATALOG_PHASE_STATUS_NOT_STARTED,
        "owner": str(owner or "").strip(),
        "triggerSource": str(trigger_source or SYNC_TRIGGER_SOURCE_BUTTON),
    }
    checkpoint = str(checkpoint or "").strip()
    if checkpoint:
        payload["checkpoint"] = checkpoint
    saved_at = str(saved_at or "").strip()
    if saved_at:
        payload["savedAt"] = saved_at
    if phase == CATALOG_SYNC_PHASE:
        saved_data = _phase_saved_data(saved_data)
        if saved_data:
            payload["savedData"] = saved_data
    else:
        base_sync_checkpoint_token = str(base_sync_checkpoint_token or "").strip()
        if base_sync_checkpoint_token:
            payload["baseSyncCheckpointToken"] = base_sync_checkpoint_token
        request_creation = _phase_request_creation(request_creation)
        if request_creation:
            payload["requestCreation"] = request_creation
    return payload


def _explicit_catalog_phase_status_from_progress(progress, phase):
    phase_statuses = progress.get("phaseStatuses")
    if not isinstance(phase_statuses, dict):
        return ""
    status = str(phase_statuses.get(phase) or "").strip()
    if status in CATALOG_PHASE_STATUSES:
        return status
    return ""
