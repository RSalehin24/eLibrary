

def pause_sync(sync_key=None):
    sync_key = sync_key or active_sync_scope()
    state = get_sync_state(sync_key)
    if state.status == ProcessingSyncStatus.SYNCING:
        run_mode = sync_run_mode(state)
        state.status = ProcessingSyncStatus.PAUSING
        if (
            state.singleton_key == PROCESSING_SYNC_KEY_CATALOG
            and sync_phase(state) == CATALOG_REQUEST_CREATION_PHASE
        ):
            state.progress = build_catalog_request_creation_progress(
                state,
                request_creation=(
                    catalog_request_creation_progress(state)
                    or initial_catalog_request_creation_progress(state)
                ),
                run_mode=run_mode,
                trigger_source=sync_trigger_source(state),
                request_creation_phase_status=CATALOG_PHASE_STATUS_PAUSING,
                sync_phase_state=catalog_phase_state(state, CATALOG_SYNC_PHASE),
            )
            state.message = catalog_request_creation_pause_request_message()
        else:
            state.progress = build_catalog_sync_progress(
                state,
                run_mode,
                next_page_index=state.page_index,
                fetched_count=state.fetched_count,
                live_fetch=sync_uses_live_fetch(state),
                trigger_source=sync_trigger_source(state),
                session_id=sync_saved_data(state).get("sessionId") or "",
                sync_phase_status=CATALOG_PHASE_STATUS_PAUSING,
                request_creation_phase_state=catalog_phase_state(
                    state,
                    CATALOG_REQUEST_CREATION_PHASE,
                ),
            )
            state.message = sync_pause_message(run_mode)
        save_sync_state(
            state,
            update_fields=["status", "progress", "message", "updated_at"],
        )
        update_automation_run_status(run_mode, state.message)
    return state


def resume_sync(sync_key=PROCESSING_SYNC_KEY_CATALOG, *, run_mode=None):
    state = get_sync_state(sync_key)
    run_mode = run_mode or sync_run_mode(state)
    live_fetch = sync_uses_live_fetch(state)
    trigger_source = sync_trigger_source(state)
    if run_mode == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        state.remote_pages = [] if live_fetch else incomplete_sync_remote_pages()
        next_page_index = 0
        fetched_count = int(state.fetched_count or 0)
        resume_message = "Restarting incomplete catalog sync from the beginning."
    elif sync_key == PROCESSING_SYNC_KEY_CATALOG:
        sync_phase_state = catalog_phase_state(state, CATALOG_SYNC_PHASE)
        request_creation_phase_state = catalog_phase_state(
            state,
            CATALOG_REQUEST_CREATION_PHASE,
        )
        saved_data = _phase_saved_data(sync_phase_state.get("savedData"))
        request_creation = _phase_request_creation(
            request_creation_phase_state.get("requestCreation")
        )
        sync_can_resume = (
            state.status == ProcessingSyncStatus.PAUSED
            and catalog_sync_phase_status(state) == CATALOG_PHASE_STATUS_PAUSED
        )
        next_page_index = int(
            saved_data.get("nextPageIndex", state.page_index or 0) or 0
        )
        fetched_count = int(saved_data.get("fetchedCount", state.fetched_count or 0) or 0)
        if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION and catalog_request_creation_can_resume(
            state
        ):
            state.status = ProcessingSyncStatus.SYNCING
            state.page_index = next_page_index
            state.fetched_count = fetched_count
            state.progress = build_catalog_request_creation_progress(
                state,
                request_creation=request_creation,
                run_mode=run_mode,
                trigger_source=trigger_source,
                request_creation_phase_status=CATALOG_PHASE_STATUS_RUNNING,
                sync_phase_state=sync_phase_state,
            )
            state.task_id = ""
            state.queue_name = ""
            state.message = catalog_request_creation_resume_message()
            save_sync_state(
                state,
                update_fields=[
                    "status",
                    "progress",
                    "page_index",
                    "fetched_count",
                    "task_id",
                    "queue_name",
                    "message",
                    "updated_at",
                ],
            )
            update_automation_run_status(run_mode, state.message)
            if should_enqueue_processing_sync_work():
                dispatch_sync_task(state, force=True)
            elif should_run_processing_jobs_inline():
                run_processing_sync_until_blocked(
                    singleton_key=state.singleton_key,
                    task_id="",
                )
            return state
        if sync_can_resume:
            resume_message = catalog_sync_resume_message(run_mode)
        else:
            next_page_index = 0
            fetched_count = 0
            resume_message = (
                "Restarting automated catalog sync from the beginning."
                if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION
                else "Restarting catalog sync from the beginning."
            )
            saved_data = {}
            request_creation_phase_state = (
                request_creation_phase_state
                if request_creation_phase_state.get("status") == CATALOG_PHASE_STATUS_PAUSED
                else None
            )
    else:
        next_page_index = 0
        fetched_count = int(state.fetched_count or 0)
        resume_message = (
            "Restarting automated catalog sync from the beginning."
            if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION
            else "Reconciling saved records from the beginning."
        )
    state.status = ProcessingSyncStatus.SYNCING
    if sync_key == PROCESSING_SYNC_KEY_CATALOG:
        state.progress = build_catalog_sync_progress(
            state,
            run_mode,
            next_page_index=next_page_index,
            fetched_count=fetched_count,
            live_fetch=live_fetch,
            trigger_source=trigger_source,
            session_id=saved_data.get("sessionId") or str(uuid4()),
            sync_phase_status=CATALOG_PHASE_STATUS_RUNNING,
            request_creation_phase_state=request_creation_phase_state,
        )
    else:
        state.progress = build_sync_progress(
            run_mode,
            next_page_index=next_page_index,
            fetched_count=fetched_count,
            live_fetch=live_fetch,
            trigger_source=trigger_source,
            session_id="",
        )
    state.page_index = next_page_index
    state.fetched_count = fetched_count
    if next_page_index == 0 and fetched_count == 0 and sync_key == PROCESSING_SYNC_KEY_CATALOG:
        state.skipped_count = 0
        state.updated_count = 0
        state.appended_count = 0
    state.task_id = ""
    state.queue_name = ""
    state.message = resume_message
    save_sync_state(
        state,
        update_fields=[
            "remote_pages",
            "status",
            "progress",
            "page_index",
            "fetched_count",
            "skipped_count",
            "updated_count",
            "appended_count",
            "task_id",
            "queue_name",
            "message",
            "updated_at",
        ]
    )
    update_automation_run_status(run_mode, state.message)
    if should_enqueue_processing_sync_work():
        dispatch_sync_task(state, force=True)
    elif should_run_processing_jobs_inline():
        run_processing_sync_until_blocked(singleton_key=state.singleton_key, task_id="")
    return state


def stop_sync(sync_key=None):
    sync_key = sync_key or active_sync_scope()
    state = get_sync_state(sync_key)
    if state.status not in {
        ProcessingSyncStatus.SYNCING,
        ProcessingSyncStatus.PAUSING,
        ProcessingSyncStatus.PAUSED,
    }:
        return state

    run_mode = sync_run_mode(state)
    state.status = ProcessingSyncStatus.IDLE
    state.progress = None
    state.task_id = ""
    state.queue_name = ""
    state.message = f"{sync_run_label(run_mode)} stopped."
    save_sync_state(
        state,
        update_fields=[
            "status",
            "progress",
            "task_id",
            "queue_name",
            "message",
            "updated_at",
        ]
    )
    update_automation_run_status(run_mode, state.message)
    return state


def finalize_sync(state, *, message=None, progress=None):
    state.status = ProcessingSyncStatus.IDLE
    state.progress = progress
    state.task_id = ""
    state.queue_name = ""
    state.message = message or (
        f"Sync complete. Updated {state.updated_count}, "
        f"Skipped {state.skipped_count}, Added {state.appended_count}."
    )
    save_sync_state(
        state,
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
        ]
    )
    return state
