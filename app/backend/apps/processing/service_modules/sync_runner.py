from django.conf import settings
from django.utils import timezone

from ..models import ProcessingSyncState, ProcessingSyncStatus
from . import automation_advancement as _automation
from . import catalog_progress_state as _progress
from . import catalog_record_sync as _catalog_sync
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import incomplete_resolution as _incomplete
from . import service_imports_and_constants as _constants
from . import state_serializers as _state
from . import sync_completion as _completion
from . import sync_status_messages as _messages


def advance_incomplete_sync_once(state):
    if _checkpoints.sync_uses_live_fetch(state):
        try:
            return _incomplete.advance_live_incomplete_sync_once(state)
        except Exception as exc:
            _constants.logger.exception("Live incomplete sync failed.")
            return _completion.fail_sync(state, exc)

    page = (
        state.remote_pages[state.page_index]
        if state.page_index < len(state.remote_pages)
        else []
    )
    if not page:
        resolved = _incomplete.resolve_incomplete_records(
            _incomplete.stale_incomplete_record_ids(state.remote_pages)
        )
        state.updated_count = len(resolved)
        _checkpoints.save_sync_state(
            state, update_fields=["updated_count", "updated_at"]
        )
        return _incomplete.complete_incomplete_automation(
            state, resolved_count=len(resolved)
        )

    if isinstance(page, list) and all(not isinstance(item, dict) for item in page):
        resolved = _incomplete.resolve_incomplete_records(page)
        state.fetched_count += len(page)
        state.updated_count += len(resolved)
        state.page_index += 1
        next_page = (
            state.remote_pages[state.page_index]
            if state.page_index < len(state.remote_pages)
            else []
        )
        latest_status = _state.persisted_sync_status(state)
        if latest_status == ProcessingSyncStatus.PAUSING:
            state.status = ProcessingSyncStatus.PAUSED
            state.progress = _messages.build_sync_progress(
                _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
                next_page_index=state.page_index,
                fetched_count=state.fetched_count,
                saved_at=timezone.now().isoformat(),
                live_fetch=_checkpoints.sync_uses_live_fetch(state),
                trigger_source=_progress.sync_trigger_source(state),
            )
            state.message = (
                f"Saved progress for {state.fetched_count} "
                f"{'record' if state.fetched_count == 1 else 'records'} before pausing."
            )
            _messages.update_automation_run_status(
                _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
                state.message,
            )
        elif latest_status != ProcessingSyncStatus.SYNCING:
            return ProcessingSyncState.objects.get(pk=state.pk)
        elif not next_page:
            return _incomplete.complete_incomplete_automation(
                state, resolved_count=state.updated_count
            )
        else:
            state.progress = _messages.build_sync_progress(
                _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
                next_page_index=state.page_index,
                fetched_count=state.fetched_count,
                live_fetch=_checkpoints.sync_uses_live_fetch(state),
                trigger_source=_progress.sync_trigger_source(state),
            )
            state.message = _messages.sync_progress_message(
                _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
                state.fetched_count,
            )
        _checkpoints.save_sync_state(state)
        return state

    result = _catalog_sync.upsert_remote_records(page)
    state.fetched_count += len(page)
    state.skipped_count += result["skipped_count"]
    state.appended_count += result["appended_count"]
    state.page_index += 1
    next_page = (
        state.remote_pages[state.page_index]
        if state.page_index < len(state.remote_pages)
        else []
    )
    latest_status = _state.persisted_sync_status(state)
    if latest_status == ProcessingSyncStatus.PAUSING:
        state.status = ProcessingSyncStatus.PAUSED
        state.progress = _messages.build_sync_progress(
            _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            next_page_index=state.page_index,
            fetched_count=state.fetched_count,
            saved_at=timezone.now().isoformat(),
            live_fetch=_checkpoints.sync_uses_live_fetch(state),
            trigger_source=_progress.sync_trigger_source(state),
        )
        state.message = (
            f"Saved progress for {state.fetched_count} "
            f"{'record' if state.fetched_count == 1 else 'records'} before pausing."
        )
        _messages.update_automation_run_status(
            _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            state.message,
        )
    elif latest_status != ProcessingSyncStatus.SYNCING:
        return ProcessingSyncState.objects.get(pk=state.pk)
    elif not next_page:
        resolved = _incomplete.resolve_incomplete_records(
            _incomplete.stale_incomplete_record_ids(state.remote_pages)
        )
        state.updated_count = len(resolved)
        _checkpoints.save_sync_state(
            state, update_fields=["updated_count", "updated_at"]
        )
        return _incomplete.complete_incomplete_automation(
            state, resolved_count=len(resolved)
        )
    else:
        state.progress = _messages.build_sync_progress(
            _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            next_page_index=state.page_index,
            fetched_count=state.fetched_count,
            live_fetch=_checkpoints.sync_uses_live_fetch(state),
            trigger_source=_progress.sync_trigger_source(state),
        )
        state.message = _messages.sync_progress_message(
            _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            state.fetched_count,
        )
    _checkpoints.save_sync_state(state)
    return state


def run_processing_sync(
    singleton_key=_constants.PROCESSING_SYNC_KEY_CATALOG, task_id=""
):
    state = ProcessingSyncState.objects.get(singleton_key=singleton_key)
    if task_id and state.task_id and state.task_id != task_id:
        return state
    if state.status not in _constants.SYNC_ACTIVE_STATUSES:
        return state

    run_mode = _progress.sync_run_mode(state)
    if run_mode == _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        return advance_incomplete_sync_once(state)
    if _progress.sync_phase(state) == _constants.CATALOG_REQUEST_CREATION_PHASE:
        return _automation.advance_catalog_request_creation_once(state)
    if not _checkpoints.sync_uses_live_fetch(state):
        return _incomplete.advance_catalog_sync_once(state, run_mode)

    return run_processing_sync_until_blocked(
        singleton_key=singleton_key, task_id=task_id
    )


def run_processing_sync_until_blocked(
    singleton_key=_constants.PROCESSING_SYNC_KEY_CATALOG,
    task_id="",
):
    state = ProcessingSyncState.objects.get(singleton_key=singleton_key)
    if task_id and state.task_id and state.task_id != task_id:
        return state
    if state.status not in _constants.SYNC_ACTIVE_STATUSES:
        return state

    run_mode = _progress.sync_run_mode(state)
    if run_mode == _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        while True:
            state.refresh_from_db()
            if task_id and state.task_id and state.task_id != task_id:
                return state
            if state.status not in _constants.SYNC_ACTIVE_STATUSES:
                return state
            state = advance_incomplete_sync_once(state)
            if state.status not in _constants.SYNC_ACTIVE_STATUSES:
                return state
    if not _checkpoints.sync_uses_live_fetch(state):
        while True:
            state.refresh_from_db()
            if task_id and state.task_id and state.task_id != task_id:
                return state
            if state.status not in _constants.SYNC_ACTIVE_STATUSES:
                return state
            state = _incomplete.advance_catalog_processing_once(state, run_mode)
            if state.status not in _constants.SYNC_ACTIVE_STATUSES:
                return state

    try:
        result = _catalog_sync.refresh_catalog_parallel()
        state.refresh_from_db()
        if task_id and state.task_id and state.task_id != task_id:
            return state
        if state.status not in _constants.SYNC_ACTIVE_STATUSES:
            return state

        state.fetched_count += result["total"]
        state.appended_count += result["appended_count"]
        state.updated_count += result["updated_count"]

        session_id = _progress.sync_saved_data(state).get("sessionId") or ""
        request_creation_phase_state = _progress.catalog_phase_state(
            state,
            _constants.CATALOG_REQUEST_CREATION_PHASE,
        )
        latest_status = _state.persisted_sync_status(state)

        if latest_status == ProcessingSyncStatus.PAUSING:
            state.status = ProcessingSyncStatus.PAUSED
            state.progress = _messages.build_catalog_sync_progress(
                state,
                run_mode,
                fetched_count=state.fetched_count,
                saved_at=timezone.now().isoformat(),
                live_fetch=True,
                trigger_source=_progress.sync_trigger_source(state),
                session_id=session_id,
                sync_phase_status=_constants.CATALOG_PHASE_STATUS_PAUSED,
                request_creation_phase_state=request_creation_phase_state,
            )
            state.message = (
                f"Sync progress saved. {_messages.catalog_record_total_message()}"
            )
            _checkpoints.save_sync_state(state)
            _messages.update_automation_run_status(run_mode, state.message)
            return state

        if latest_status != ProcessingSyncStatus.SYNCING:
            return ProcessingSyncState.objects.get(pk=state.pk)

        if run_mode == _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION:
            state = _completion.begin_catalog_request_creation(state)
            if state.status not in _constants.SYNC_ACTIVE_STATUSES:
                return state

        return _completion.finalize_catalog_sync(state, run_mode=run_mode)
    except Exception as exc:
        _constants.logger.exception(
            "Live processing sync failed.", extra={"task_id": task_id}
        )
        return _completion.fail_sync(state, exc)


def advance_sync_once(sync_key=None):
    sync_key = sync_key or _state.active_sync_scope()
    state = _state.get_sync_state(sync_key)
    if state.status not in _constants.SYNC_ACTIVE_STATUSES:
        return state
    if state.task_id and not settings.CELERY_TASK_ALWAYS_EAGER:
        return state
    return run_processing_sync(singleton_key=state.singleton_key, task_id=state.task_id)


def request_id_for_record(record):
    return f"request-{record.id}"
