from ..models import ProcessingSyncStatus
from . import catalog_phase_helpers as _phase_helpers
from . import catalog_progress_state as _progress
from . import service_imports_and_constants as _constants


def _legacy_catalog_phase_states(progress, runtime_status):
    saved_data = _phase_helpers._phase_saved_data(progress.get("savedData"))
    request_creation = _phase_helpers._phase_request_creation(
        progress.get("requestCreation")
    )
    run_mode = (
        str(progress.get("runMode") or "").strip()
        or str(saved_data.get("runMode") or "").strip()
        or _constants.SYNC_RUN_MODE_MANUAL
    )
    trigger_source = (
        str(progress.get("triggerSource") or "").strip()
        or str(saved_data.get("triggerSource") or "").strip()
        or _constants.SYNC_TRIGGER_SOURCE_BUTTON
    )
    progress_phase = (
        str(progress.get("phase") or _constants.CATALOG_SYNC_PHASE).strip()
        or _constants.CATALOG_SYNC_PHASE
    )
    sync_status = _phase_helpers._explicit_catalog_phase_status_from_progress(
        progress, _constants.CATALOG_SYNC_PHASE
    )
    if not sync_status:
        if progress_phase == _constants.CATALOG_REQUEST_CREATION_PHASE:
            sync_status = _constants.CATALOG_PHASE_STATUS_COMPLETED
        elif runtime_status == ProcessingSyncStatus.PAUSED:
            sync_status = _constants.CATALOG_PHASE_STATUS_PAUSED
        elif runtime_status in _constants.SYNC_ACTIVE_STATUSES:
            sync_status = _constants.CATALOG_PHASE_STATUS_RUNNING
        elif saved_data:
            sync_status = _constants.CATALOG_PHASE_STATUS_COMPLETED
        else:
            sync_status = _constants.CATALOG_PHASE_STATUS_NOT_STARTED
    sync_status = _phase_helpers._catalog_phase_status_from_runtime(
        sync_status,
        runtime_status,
        _constants.CATALOG_SYNC_PHASE,
        progress_phase,
    )
    request_creation_status = (
        _phase_helpers._explicit_catalog_phase_status_from_progress(
            progress,
            _constants.CATALOG_REQUEST_CREATION_PHASE,
        )
    )
    if not request_creation_status:
        if progress_phase == _constants.CATALOG_REQUEST_CREATION_PHASE:
            if runtime_status == ProcessingSyncStatus.PAUSED:
                request_creation_status = _constants.CATALOG_PHASE_STATUS_PAUSED
            elif runtime_status in _constants.SYNC_ACTIVE_STATUSES:
                request_creation_status = _constants.CATALOG_PHASE_STATUS_RUNNING
            else:
                request_creation_status = _constants.CATALOG_PHASE_STATUS_COMPLETED
        else:
            request_creation_status = _constants.CATALOG_PHASE_STATUS_NOT_STARTED
    request_creation_status = _phase_helpers._catalog_phase_status_from_runtime(
        request_creation_status,
        runtime_status,
        _constants.CATALOG_REQUEST_CREATION_PHASE,
        progress_phase,
    )
    sync_checkpoint = ""
    if progress_phase == _constants.CATALOG_SYNC_PHASE:
        sync_checkpoint = str(progress.get("checkpoint") or "").strip()
    if not sync_checkpoint:
        sync_checkpoint = _phase_helpers._catalog_phase_checkpoint_from_saved_data(
            saved_data
        )
    sync_saved_at = (
        str(progress.get("savedAt") or "").strip()
        if progress_phase == _constants.CATALOG_SYNC_PHASE
        else ""
    )
    request_creation_checkpoint = ""
    request_creation_saved_at = ""
    if progress_phase == _constants.CATALOG_REQUEST_CREATION_PHASE:
        request_creation_checkpoint = str(progress.get("checkpoint") or "").strip()
        request_creation_saved_at = str(progress.get("savedAt") or "").strip()
    if not request_creation_checkpoint and request_creation:
        request_creation_checkpoint = f"request-{request_creation.get('lastRecordId') or request_creation.get('processedCount', 0)}"
    request_creation_base_token = (
        str(progress.get("baseSyncCheckpointToken") or "").strip()
        or _progress.request_creation_base_checkpoint_token(request_creation)
        or _phase_helpers._catalog_phase_checkpoint_from_saved_data(saved_data)
    )
    sync_status, request_creation_status = (
        _phase_helpers._normalize_catalog_phase_status_pair(
            sync_status,
            request_creation_status,
            progress_phase=progress_phase,
            request_creation=request_creation,
            request_creation_base_token=request_creation_base_token,
            request_creation_checkpoint=request_creation_checkpoint,
        )
    )
    return {
        _constants.CATALOG_SYNC_PHASE: _phase_helpers._catalog_phase_state(
            _constants.CATALOG_SYNC_PHASE,
            status=sync_status,
            owner=run_mode
            if sync_status != _constants.CATALOG_PHASE_STATUS_NOT_STARTED
            else "",
            trigger_source=trigger_source,
            checkpoint=sync_checkpoint,
            saved_at=sync_saved_at,
            saved_data={
                **saved_data,
                **({"runMode": run_mode} if run_mode else {}),
                **({"triggerSource": trigger_source} if trigger_source else {}),
            }
            if saved_data
            else {},
        ),
        _constants.CATALOG_REQUEST_CREATION_PHASE: _phase_helpers._catalog_phase_state(
            _constants.CATALOG_REQUEST_CREATION_PHASE,
            status=request_creation_status,
            owner=(
                run_mode
                if request_creation_status
                != _constants.CATALOG_PHASE_STATUS_NOT_STARTED
                else ""
            ),
            trigger_source=trigger_source,
            checkpoint=request_creation_checkpoint,
            saved_at=request_creation_saved_at,
            request_creation=request_creation,
            base_sync_checkpoint_token=request_creation_base_token,
        ),
    }


def _normalized_catalog_phase_states(progress, runtime_status):
    phase_states = progress.get("phaseStates")
    if not isinstance(phase_states, dict):
        return _legacy_catalog_phase_states(progress, runtime_status)
    sync_phase_state = phase_states.get(_constants.CATALOG_SYNC_PHASE)
    request_creation_phase_state = phase_states.get(
        _constants.CATALOG_REQUEST_CREATION_PHASE
    )
    normalized_sync_saved_data = _phase_helpers._phase_saved_data(
        sync_phase_state.get("savedData")
        if isinstance(sync_phase_state, dict)
        else None
    )
    if normalized_sync_saved_data:
        normalized_sync_saved_data = {
            **normalized_sync_saved_data,
            **(
                {"runMode": str(sync_phase_state.get("owner") or "").strip()}
                if str(sync_phase_state.get("owner") or "").strip()
                else {}
            ),
            **(
                {
                    "triggerSource": str(
                        sync_phase_state.get("triggerSource") or ""
                    ).strip()
                }
                if str(sync_phase_state.get("triggerSource") or "").strip()
                else {}
            ),
        }
    normalized_request_creation = _phase_helpers._phase_request_creation(
        request_creation_phase_state.get("requestCreation")
        if isinstance(request_creation_phase_state, dict)
        else None
    )
    request_creation_base_token = (
        str(request_creation_phase_state.get("baseSyncCheckpointToken") or "").strip()
        if isinstance(request_creation_phase_state, dict)
        else ""
    ) or _progress.request_creation_base_checkpoint_token(normalized_request_creation)
    progress_phase = (
        str(progress.get("phase") or _constants.CATALOG_SYNC_PHASE).strip()
        or _constants.CATALOG_SYNC_PHASE
    )
    sync_status = _phase_helpers._catalog_phase_status_from_runtime(
        (
            sync_phase_state.get("status")
            if isinstance(sync_phase_state, dict)
            else _constants.CATALOG_PHASE_STATUS_NOT_STARTED
        ),
        runtime_status,
        _constants.CATALOG_SYNC_PHASE,
        progress_phase,
    )
    request_creation_status = _phase_helpers._catalog_phase_status_from_runtime(
        (
            request_creation_phase_state.get("status")
            if isinstance(request_creation_phase_state, dict)
            else _constants.CATALOG_PHASE_STATUS_NOT_STARTED
        ),
        runtime_status,
        _constants.CATALOG_REQUEST_CREATION_PHASE,
        progress_phase,
    )
    request_creation_checkpoint = (
        request_creation_phase_state.get("checkpoint")
        if isinstance(request_creation_phase_state, dict)
        else ""
    )
    sync_status, request_creation_status = (
        _phase_helpers._normalize_catalog_phase_status_pair(
            sync_status,
            request_creation_status,
            progress_phase=progress_phase,
            request_creation=normalized_request_creation,
            request_creation_base_token=request_creation_base_token,
            request_creation_checkpoint=request_creation_checkpoint,
        )
    )
    return {
        _constants.CATALOG_SYNC_PHASE: _phase_helpers._catalog_phase_state(
            _constants.CATALOG_SYNC_PHASE,
            status=sync_status,
            owner=sync_phase_state.get("owner")
            if isinstance(sync_phase_state, dict)
            else "",
            trigger_source=(
                sync_phase_state.get("triggerSource")
                if isinstance(sync_phase_state, dict)
                else _constants.SYNC_TRIGGER_SOURCE_BUTTON
            ),
            checkpoint=sync_phase_state.get("checkpoint")
            if isinstance(sync_phase_state, dict)
            else "",
            saved_at=sync_phase_state.get("savedAt")
            if isinstance(sync_phase_state, dict)
            else "",
            saved_data=normalized_sync_saved_data,
        ),
        _constants.CATALOG_REQUEST_CREATION_PHASE: _phase_helpers._catalog_phase_state(
            _constants.CATALOG_REQUEST_CREATION_PHASE,
            status=request_creation_status,
            owner=(
                request_creation_phase_state.get("owner")
                if isinstance(request_creation_phase_state, dict)
                else ""
            ),
            trigger_source=(
                request_creation_phase_state.get("triggerSource")
                if isinstance(request_creation_phase_state, dict)
                else _constants.SYNC_TRIGGER_SOURCE_BUTTON
            ),
            checkpoint=(
                request_creation_phase_state.get("checkpoint")
                if isinstance(request_creation_phase_state, dict)
                else ""
            ),
            saved_at=(
                request_creation_phase_state.get("savedAt")
                if isinstance(request_creation_phase_state, dict)
                else ""
            ),
            request_creation=normalized_request_creation,
            base_sync_checkpoint_token=request_creation_base_token,
        ),
    }


def catalog_phase_states(state):
    progress = state.progress if isinstance(state.progress, dict) else {}
    if state.singleton_key != _constants.PROCESSING_SYNC_KEY_CATALOG or not progress:
        return {
            _constants.CATALOG_SYNC_PHASE: _phase_helpers._catalog_phase_state(
                _constants.CATALOG_SYNC_PHASE
            ),
            _constants.CATALOG_REQUEST_CREATION_PHASE: _phase_helpers._catalog_phase_state(
                _constants.CATALOG_REQUEST_CREATION_PHASE
            ),
        }
    return _normalized_catalog_phase_states(progress, state.status)


def catalog_summary_phase(phase_states):
    request_creation_status = phase_states[_constants.CATALOG_REQUEST_CREATION_PHASE][
        "status"
    ]
    sync_status = phase_states[_constants.CATALOG_SYNC_PHASE]["status"]
    if _phase_helpers.catalog_phase_is_active_status(request_creation_status):
        return _constants.CATALOG_REQUEST_CREATION_PHASE
    if (
        _phase_helpers.catalog_phase_is_active_status(sync_status)
        or sync_status == _constants.CATALOG_PHASE_STATUS_PAUSED
    ):
        return _constants.CATALOG_SYNC_PHASE
    if request_creation_status == _constants.CATALOG_PHASE_STATUS_PAUSED:
        return _constants.CATALOG_REQUEST_CREATION_PHASE
    return _constants.CATALOG_SYNC_PHASE
