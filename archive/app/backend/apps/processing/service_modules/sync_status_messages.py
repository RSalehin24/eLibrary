

def catalog_record_total_message():
    total_records = BookRecord.objects.count()
    label = "book record" if total_records == 1 else "book records"
    return f"Catalog now has {total_records} {label}."


def sync_progress_message(run_mode, processed_count):
    label = "record" if processed_count == 1 else "records"
    if run_mode == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        return f"Processed {processed_count} incomplete {label} so far."
    return catalog_record_total_message()


def sync_pause_message(run_mode):
    if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION:
        return "Pausing automated catalog sync after the current page finishes."
    if run_mode == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        return "Pausing incomplete catalog sync after the current batch finishes."
    return "Pausing after the current page finishes."


def build_sync_progress(
    run_mode,
    *,
    next_page_index=0,
    fetched_count=0,
    saved_at=None,
    live_fetch=False,
    trigger_source=SYNC_TRIGGER_SOURCE_BUTTON,
    session_id="",
    request_creation=None,
    sync_phase_status=CATALOG_PHASE_STATUS_RUNNING,
    request_creation_phase_status=CATALOG_PHASE_STATUS_NOT_STARTED,
):
    session_id = str(session_id or "").strip()
    payload = {
        "runMode": run_mode,
        "triggerSource": trigger_source,
        "phase": CATALOG_SYNC_PHASE,
        "checkpoint": f"page-{next_page_index}",
        "savedData": {
            "runMode": run_mode,
            "triggerSource": trigger_source,
            "fetchedCount": fetched_count,
            "nextPageIndex": next_page_index,
        },
    }
    if session_id:
        payload["savedData"]["sessionId"] = session_id
        payload["savedData"]["checkpointToken"] = catalog_sync_checkpoint_token(
            session_id,
            next_page_index=next_page_index,
            fetched_count=fetched_count,
            live_fetch=live_fetch,
        )
    if live_fetch:
        payload["savedData"]["liveFetch"] = True
    if saved_at:
        payload["savedAt"] = saved_at
    return payload


def build_catalog_sync_progress(
    state,
    run_mode,
    *,
    next_page_index=0,
    fetched_count=0,
    saved_at=None,
    live_fetch=False,
    trigger_source=SYNC_TRIGGER_SOURCE_BUTTON,
    session_id="",
    sync_phase_status=CATALOG_PHASE_STATUS_RUNNING,
    request_creation_phase_state=None,
):
    session_id = str(session_id or "").strip()
    saved_data = {
        "runMode": run_mode,
        "triggerSource": trigger_source,
        "fetchedCount": fetched_count,
        "nextPageIndex": next_page_index,
    }
    if session_id:
        saved_data["sessionId"] = session_id
        saved_data["checkpointToken"] = catalog_sync_checkpoint_token(
            session_id,
            next_page_index=next_page_index,
            fetched_count=fetched_count,
            live_fetch=live_fetch,
        )
    if live_fetch:
        saved_data["liveFetch"] = True
    sync_phase_state = _catalog_phase_state(
        CATALOG_SYNC_PHASE,
        status=sync_phase_status,
        owner=run_mode,
        trigger_source=trigger_source,
        checkpoint=f"page-{next_page_index}",
        saved_at=saved_at,
        saved_data=saved_data,
    )
    current_request_creation_phase_state = (
        request_creation_phase_state
        if isinstance(request_creation_phase_state, dict)
        else catalog_phase_state(state, CATALOG_REQUEST_CREATION_PHASE)
    )
    request_creation_status = current_request_creation_phase_state.get("status")
    if request_creation_status == CATALOG_PHASE_STATUS_PAUSED:
        next_request_creation_phase_state = replace_catalog_phase_state(
            CATALOG_REQUEST_CREATION_PHASE,
            current_request_creation_phase_state,
        )
    else:
        next_request_creation_phase_state = _catalog_phase_state(
            CATALOG_REQUEST_CREATION_PHASE,
            status=CATALOG_PHASE_STATUS_NOT_STARTED,
        )
    return build_catalog_progress_payload(
        {
            CATALOG_SYNC_PHASE: sync_phase_state,
            CATALOG_REQUEST_CREATION_PHASE: next_request_creation_phase_state,
        }
    )


def build_catalog_request_creation_progress(
    state,
    *,
    request_creation,
    run_mode=SYNC_RUN_MODE_CATALOG_AUTOMATION,
    trigger_source=SYNC_TRIGGER_SOURCE_BUTTON,
    saved_at=None,
    request_creation_phase_status=CATALOG_PHASE_STATUS_RUNNING,
    sync_phase_state=None,
):
    current_sync_phase_state = (
        sync_phase_state
        if isinstance(sync_phase_state, dict)
        else replace_catalog_phase_state(
            CATALOG_SYNC_PHASE,
            catalog_phase_state(state, CATALOG_SYNC_PHASE),
            status=CATALOG_PHASE_STATUS_COMPLETED,
            owner=(
                catalog_phase_state(state, CATALOG_SYNC_PHASE).get("owner")
                or run_mode
            ),
            trigger_source=(
                catalog_phase_state(state, CATALOG_SYNC_PHASE).get("triggerSource")
                or trigger_source
            ),
            checkpoint=(
                catalog_phase_state(state, CATALOG_SYNC_PHASE).get("checkpoint")
                or f"page-{sync_saved_data(state).get('nextPageIndex') or state.page_index or 0}"
            ),
            saved_data=(
                _phase_saved_data(catalog_phase_state(state, CATALOG_SYNC_PHASE).get("savedData"))
                or {
                    **sync_saved_data(state),
                    "runMode": (
                        catalog_phase_state(state, CATALOG_SYNC_PHASE).get("owner")
                        or run_mode
                    ),
                    "triggerSource": (
                        catalog_phase_state(state, CATALOG_SYNC_PHASE).get("triggerSource")
                        or trigger_source
                    ),
                }
            ),
        )
    )
    request_creation_checkpoint = (
        f"request-{request_creation.get('lastRecordId') or request_creation.get('processedCount', 0)}"
    )
    base_sync_checkpoint_token = (
        request_creation_base_checkpoint_token(request_creation)
        or _catalog_phase_checkpoint_from_saved_data(
            _phase_saved_data(current_sync_phase_state.get("savedData"))
        )
    )
    next_request_creation_phase_state = _catalog_phase_state(
        CATALOG_REQUEST_CREATION_PHASE,
        status=request_creation_phase_status,
        owner=run_mode,
        trigger_source=trigger_source,
        checkpoint=request_creation_checkpoint,
        saved_at=saved_at,
        request_creation=request_creation,
        base_sync_checkpoint_token=base_sync_checkpoint_token,
    )
    return build_catalog_progress_payload(
        {
            CATALOG_SYNC_PHASE: current_sync_phase_state,
            CATALOG_REQUEST_CREATION_PHASE: next_request_creation_phase_state,
        }
    )


def catalog_sync_resume_message(run_mode):
    if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION:
        return "Continuing automated catalog sync from the saved endpoint."
    return "Continuing catalog sync from the saved endpoint."


def catalog_request_creation_start_message():
    return "Creating book requests from the synced catalog records."


def catalog_request_creation_resume_message():
    return "Resuming automated request creation from saved progress."


def catalog_request_creation_pause_request_message():
    return "Pausing automated request creation after the current batch finishes."


def catalog_request_creation_pause_message(request_creation):
    processed_count = int(request_creation.get("processedCount") or 0)
    label = "record" if processed_count == 1 else "records"
    return (
        f"Saved request creation progress after scanning {processed_count} {label}."
    )


def catalog_request_creation_progress_message(request_creation):
    processed_count = int(request_creation.get("processedCount") or 0)
    created_count = int(request_creation.get("createdCount") or 0)
    return (
        f"Scanned {processed_count} catalog "
        f"{'record' if processed_count == 1 else 'records'}; "
        f"created {created_count} "
        f"{'request' if created_count == 1 else 'requests'} so far."
    )


def update_automation_run_status(run_mode, message, *, last_run_at=None):
    if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION:
        automation_settings = get_automation_settings(ProcessingAutomationKind.CATALOG)
    elif run_mode == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        automation_settings = get_automation_settings(ProcessingAutomationKind.INCOMPLETE)
    else:
        return None

    update_fields = ["status_message", "updated_at"]
    automation_settings.status_message = message
    if last_run_at is not None:
        automation_settings.last_run_at = last_run_at
        update_fields.append("last_run_at")
    if automation_settings.pk is None:
        automation_settings.save()
    else:
        automation_settings.save(update_fields=update_fields)
    publish_processing_ui_domains(processing_domains_for_automation(automation_settings.kind))
    return automation_settings
