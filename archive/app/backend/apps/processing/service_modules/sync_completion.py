

def fail_sync(state, error):
    run_mode = sync_run_mode(state)
    state.status = ProcessingSyncStatus.IDLE
    state.progress = None
    state.task_id = ""
    state.queue_name = ""
    state.last_error = str(error)
    state.message = f"{sync_run_label(run_mode)} failed: {error}"
    save_sync_state(
        state,
        update_fields=[
            "status",
            "progress",
            "task_id",
            "queue_name",
            "last_error",
            "message",
            "updated_at",
        ]
    )
    update_automation_run_status(run_mode, state.message)
    return state


def catalog_progress_after_completion(
    state,
    *,
    run_mode,
    request_creation_phase_status=CATALOG_PHASE_STATUS_NOT_STARTED,
):
    current_sync_phase_state = catalog_phase_state(state, CATALOG_SYNC_PHASE)
    current_request_creation_phase_state = catalog_phase_state(
        state,
        CATALOG_REQUEST_CREATION_PHASE,
    )
    sync_saved_data = {
        **_phase_saved_data(current_sync_phase_state.get("savedData")),
        "runMode": run_mode,
        "triggerSource": sync_trigger_source(state),
    }
    sync_phase_state = replace_catalog_phase_state(
        CATALOG_SYNC_PHASE,
        current_sync_phase_state,
        status=CATALOG_PHASE_STATUS_COMPLETED,
        owner=run_mode,
        trigger_source=sync_trigger_source(state),
        checkpoint=(
            current_sync_phase_state.get("checkpoint")
            or f"page-{sync_saved_data.get('nextPageIndex') or state.page_index or 0}"
        ),
        saved_data=sync_saved_data,
        saved_at="",
    )
    if request_creation_phase_status == CATALOG_PHASE_STATUS_COMPLETED:
        request_creation_phase_state = _catalog_phase_state(
            CATALOG_REQUEST_CREATION_PHASE,
            status=CATALOG_PHASE_STATUS_COMPLETED,
            owner=SYNC_RUN_MODE_CATALOG_AUTOMATION,
            trigger_source=(
                current_request_creation_phase_state.get("triggerSource")
                or sync_trigger_source(state)
            ),
            base_sync_checkpoint_token=(
                current_request_creation_phase_state.get("baseSyncCheckpointToken")
                or _catalog_phase_checkpoint_from_saved_data(sync_saved_data)
            ),
        )
    elif current_request_creation_phase_state.get("status") == CATALOG_PHASE_STATUS_PAUSED:
        request_creation_phase_state = replace_catalog_phase_state(
            CATALOG_REQUEST_CREATION_PHASE,
            current_request_creation_phase_state,
        )
    else:
        request_creation_phase_state = _catalog_phase_state(
            CATALOG_REQUEST_CREATION_PHASE,
            status=CATALOG_PHASE_STATUS_NOT_STARTED,
        )
    return build_catalog_progress_payload(
        {
            CATALOG_SYNC_PHASE: sync_phase_state,
            CATALOG_REQUEST_CREATION_PHASE: request_creation_phase_state,
        }
    )


def finalize_catalog_sync(state, *, run_mode):
    progress = catalog_progress_after_completion(
        state,
        run_mode=run_mode,
    )
    phase_states = _normalized_catalog_phase_states(progress, ProcessingSyncStatus.IDLE)
    return persist_catalog_phase_states(
        state,
        phase_states,
        message=(
            f"Sync complete. Updated {state.updated_count}, "
            f"Skipped {state.skipped_count}, Added {state.appended_count}."
        ),
        update_fields=[
            "status",
            "progress",
            "task_id",
            "queue_name",
            "message",
            "page_index",
            "fetched_count",
            "skipped_count",
            "updated_count",
            "appended_count",
            "updated_at",
        ],
    )


def catalog_request_creation_queryset(*, after_record_id=""):
    queryset = BookRecord.objects.order_by("id")
    if after_record_id:
        queryset = queryset.filter(id__gt=after_record_id)
    return queryset


def begin_catalog_request_creation(state):
    current_sync_phase_state = catalog_phase_state(state, CATALOG_SYNC_PHASE)
    sync_owner = (
        current_sync_phase_state.get("owner")
        or sync_run_mode(state)
        or SYNC_RUN_MODE_CATALOG_AUTOMATION
    )
    sync_phase_trigger_source = (
        current_sync_phase_state.get("triggerSource")
        or sync_trigger_source(state)
    )
    current_sync_saved_data = (
        _phase_saved_data(current_sync_phase_state.get("savedData"))
        or sync_saved_data(state)
    )
    session_id = current_sync_saved_data.get("sessionId") or str(uuid4())
    sync_saved_data_payload = {
        **current_sync_saved_data,
        "runMode": sync_owner,
        "triggerSource": sync_phase_trigger_source,
        "fetchedCount": state.fetched_count,
        "nextPageIndex": state.page_index,
        "sessionId": session_id,
        "checkpointToken": catalog_sync_checkpoint_token(
            session_id,
            next_page_index=state.page_index,
            fetched_count=state.fetched_count,
            live_fetch=sync_uses_live_fetch(state),
        ),
    }
    if sync_uses_live_fetch(state):
        sync_saved_data_payload["liveFetch"] = True
    else:
        sync_saved_data_payload.pop("liveFetch", None)
    sync_phase_state = replace_catalog_phase_state(
        CATALOG_SYNC_PHASE,
        current_sync_phase_state,
        status=CATALOG_PHASE_STATUS_COMPLETED,
        owner=sync_owner,
        trigger_source=sync_phase_trigger_source,
        checkpoint=(
            current_sync_phase_state.get("checkpoint")
            or f"page-{state.page_index}"
        ),
        saved_at="",
        saved_data=sync_saved_data_payload,
    )
    request_creation = {
        "baseCheckpointToken": _catalog_phase_checkpoint_from_saved_data(
            _phase_saved_data(sync_phase_state.get("savedData"))
        ),
        "lastRecordId": "",
        "processedCount": 0,
        "createdCount": 0,
        "unsupportedCount": 0,
    }
    state.status = ProcessingSyncStatus.SYNCING
    state.progress = build_catalog_request_creation_progress(
        state,
        request_creation=request_creation,
        trigger_source=sync_trigger_source(state),
        request_creation_phase_status=CATALOG_PHASE_STATUS_RUNNING,
        sync_phase_state=sync_phase_state,
    )
    state.message = catalog_request_creation_start_message()
    save_sync_state(state)
    update_automation_run_status(SYNC_RUN_MODE_CATALOG_AUTOMATION, state.message)
    return state
