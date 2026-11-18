

def build_catalog_progress_payload(phase_states):
    phase_states = _normalized_catalog_phase_states(
        {"phaseStates": phase_states},
        ProcessingSyncStatus.IDLE,
    )
    summary_phase = catalog_summary_phase(phase_states)
    summary_phase_state = phase_states[summary_phase]
    sync_phase_state = phase_states[CATALOG_SYNC_PHASE]
    request_creation_phase_state = phase_states[CATALOG_REQUEST_CREATION_PHASE]
    payload = {
        "runMode": summary_phase_state.get("owner") or SYNC_RUN_MODE_MANUAL,
        "triggerSource": (
            summary_phase_state.get("triggerSource") or SYNC_TRIGGER_SOURCE_BUTTON
        ),
        "phase": summary_phase,
        "phaseStatuses": catalog_phase_statuses(
            sync_status=sync_phase_state["status"],
            request_creation_status=request_creation_phase_state["status"],
        ),
        "phaseStates": phase_states,
    }
    checkpoint = str(summary_phase_state.get("checkpoint") or "").strip()
    if checkpoint:
        payload["checkpoint"] = checkpoint
    saved_at = str(summary_phase_state.get("savedAt") or "").strip()
    if saved_at:
        payload["savedAt"] = saved_at
    sync_saved_data = _phase_saved_data(sync_phase_state.get("savedData"))
    if sync_saved_data:
        payload["savedData"] = sync_saved_data
    request_creation = _phase_request_creation(
        request_creation_phase_state.get("requestCreation")
    )
    if request_creation:
        payload["requestCreation"] = request_creation
    return payload


def catalog_phase_state(state, phase):
    return catalog_phase_states(state).get(phase, _catalog_phase_state(phase))


def replace_catalog_phase_state(phase, phase_state, **overrides):
    phase_state = phase_state if isinstance(phase_state, dict) else {}
    if phase == CATALOG_SYNC_PHASE:
        return _catalog_phase_state(
            CATALOG_SYNC_PHASE,
            status=overrides.get("status", phase_state.get("status")),
            owner=overrides.get("owner", phase_state.get("owner")),
            trigger_source=overrides.get(
                "trigger_source",
                phase_state.get("triggerSource"),
            ),
            checkpoint=overrides.get("checkpoint", phase_state.get("checkpoint")),
            saved_at=overrides.get("saved_at", phase_state.get("savedAt")),
            saved_data=overrides.get("saved_data", phase_state.get("savedData")),
        )
    return _catalog_phase_state(
        CATALOG_REQUEST_CREATION_PHASE,
        status=overrides.get("status", phase_state.get("status")),
        owner=overrides.get("owner", phase_state.get("owner")),
        trigger_source=overrides.get(
            "trigger_source",
            phase_state.get("triggerSource"),
        ),
        checkpoint=overrides.get("checkpoint", phase_state.get("checkpoint")),
        saved_at=overrides.get("saved_at", phase_state.get("savedAt")),
        request_creation=overrides.get(
            "request_creation",
            phase_state.get("requestCreation"),
        ),
        base_sync_checkpoint_token=overrides.get(
            "base_sync_checkpoint_token",
            phase_state.get("baseSyncCheckpointToken"),
        ),
    )


def catalog_runtime_status(phase_states):
    statuses = {
        phase_states[CATALOG_SYNC_PHASE]["status"],
        phase_states[CATALOG_REQUEST_CREATION_PHASE]["status"],
    }
    if CATALOG_PHASE_STATUS_PAUSING in statuses:
        return ProcessingSyncStatus.PAUSING
    if CATALOG_PHASE_STATUS_RUNNING in statuses:
        return ProcessingSyncStatus.SYNCING
    if CATALOG_PHASE_STATUS_PAUSED in statuses:
        return ProcessingSyncStatus.PAUSED
    return ProcessingSyncStatus.IDLE


def persist_catalog_phase_states(
    state,
    phase_states,
    *,
    message=None,
    update_fields=None,
):
    state.status = catalog_runtime_status(phase_states)
    state.progress = build_catalog_progress_payload(phase_states)
    state.task_id = ""
    state.queue_name = ""
    if message is not None:
        state.message = message
    save_sync_state(
        state,
        update_fields=update_fields
        or [
            "status",
            "progress",
            "task_id",
            "queue_name",
            "message",
            "updated_at",
        ],
    )
    return state


def sync_run_mode(state):
    progress = sync_progress_payload(state)
    saved_data = _phase_saved_data(progress.get("savedData"))
    return progress.get("runMode") or saved_data.get("runMode") or SYNC_RUN_MODE_MANUAL


def sync_trigger_source(state):
    progress = sync_progress_payload(state)
    saved_data = _phase_saved_data(progress.get("savedData"))
    return (
        progress.get("triggerSource")
        or saved_data.get("triggerSource")
        or SYNC_TRIGGER_SOURCE_BUTTON
    )


def sync_progress_payload(state):
    progress = state.progress if isinstance(state.progress, dict) else {}
    if state.singleton_key == PROCESSING_SYNC_KEY_CATALOG and progress:
        return build_catalog_progress_payload(catalog_phase_states(state))
    return progress


def sync_saved_data(state):
    saved_data = sync_progress_payload(state).get("savedData")
    return saved_data if isinstance(saved_data, dict) else {}


def sync_phase(state):
    return str(sync_progress_payload(state).get("phase") or CATALOG_SYNC_PHASE)


def _explicit_catalog_phase_status(state, phase):
    phase_statuses = sync_progress_payload(state).get("phaseStatuses")
    if not isinstance(phase_statuses, dict):
        return ""
    status = str(phase_statuses.get(phase) or "").strip()
    if status in CATALOG_PHASE_STATUSES:
        return status
    return ""


def catalog_sync_phase_status(state):
    if state.singleton_key != PROCESSING_SYNC_KEY_CATALOG:
        return CATALOG_PHASE_STATUS_NOT_STARTED
    return catalog_phase_states(state)[CATALOG_SYNC_PHASE]["status"]


def catalog_request_creation_phase_status(state):
    if state.singleton_key != PROCESSING_SYNC_KEY_CATALOG:
        return CATALOG_PHASE_STATUS_NOT_STARTED
    return catalog_phase_states(state)[CATALOG_REQUEST_CREATION_PHASE]["status"]


def catalog_request_creation_progress(state):
    request_creation = catalog_phase_states(state)[CATALOG_REQUEST_CREATION_PHASE].get(
        "requestCreation"
    )
    return request_creation if isinstance(request_creation, dict) else None


def catalog_sync_checkpoint_token(
    session_id,
    *,
    next_page_index=0,
    fetched_count=0,
    live_fetch=False,
):
    return (
        f"{session_id}:{1 if live_fetch else 0}:"
        f"{int(next_page_index)}:{int(fetched_count)}"
    )


def current_catalog_sync_checkpoint_token(state):
    return _catalog_phase_checkpoint_from_saved_data(sync_saved_data(state))


def catalog_shared_runtime(run_mode):
    return run_mode in {
        SYNC_RUN_MODE_MANUAL,
        SYNC_RUN_MODE_CATALOG_AUTOMATION,
    }


def request_creation_base_checkpoint_token(request_creation):
    if not isinstance(request_creation, dict):
        return ""
    return str(request_creation.get("baseCheckpointToken") or "").strip()


def request_creation_matches_checkpoint(request_creation, checkpoint_token):
    return bool(checkpoint_token) and request_creation_base_checkpoint_token(
        request_creation
    ) == str(checkpoint_token).strip()


def preserve_catalog_request_creation_progress(request_creation, checkpoint_token):
    if request_creation_matches_checkpoint(request_creation, checkpoint_token):
        return request_creation
    return None


def initial_catalog_request_creation_progress(state):
    return {
        "baseCheckpointToken": current_catalog_sync_checkpoint_token(state),
        "lastRecordId": "",
        "processedCount": 0,
        "createdCount": 0,
        "unsupportedCount": 0,
    }


def catalog_request_creation_can_resume(state):
    if catalog_request_creation_phase_status(state) != CATALOG_PHASE_STATUS_PAUSED:
        return False
    request_creation_phase_state = catalog_phase_states(state)[CATALOG_REQUEST_CREATION_PHASE]
    request_creation = _phase_request_creation(request_creation_phase_state.get("requestCreation"))
    checkpoint_token = str(
        request_creation_phase_state.get("baseSyncCheckpointToken") or ""
    ).strip() or request_creation_base_checkpoint_token(request_creation)
    return request_creation_matches_checkpoint(request_creation, checkpoint_token)


def catalog_saved_checkpoint_available(state):
    saved_data = sync_saved_data(state)
    return state.singleton_key == PROCESSING_SYNC_KEY_CATALOG and bool(saved_data)


def sync_key_for_run_mode(run_mode):
    if run_mode == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        return PROCESSING_SYNC_KEY_INCOMPLETE
    return PROCESSING_SYNC_KEY_CATALOG
