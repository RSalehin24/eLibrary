from apps.ingestion.models import SubmissionOrigin
from django.utils import timezone

from ..models import (
    BookCreationState,
    ProcessingSyncState,
    ProcessingSyncStatus,
)
from . import automation_commands as _automation_commands
from . import catalog_phase_helpers as _phase_helpers
from . import catalog_progress_state as _progress
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import incomplete_catalog_queries as _incomplete_catalog_queries
from . import processing_state_queries as _queries
from . import service_imports_and_constants as _constants
from . import state_serializers as _state
from . import sync_completion as _completion
from . import sync_status_messages as _messages


def complete_catalog_automation(state, *, request_creation):
    created_count = int(request_creation.get("createdCount") or 0)
    unsupported_count = int(request_creation.get("unsupportedCount") or 0)
    finished_at = timezone.now()
    status_message = (
        f"Created {created_count} {'request' if created_count == 1 else 'requests'}."
    )
    if unsupported_count:
        status_message = (
            f"{status_message} Skipped {unsupported_count} unsupported "
            f"{'record' if unsupported_count == 1 else 'records'}."
        )
    _messages.update_automation_run_status(
        _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
        status_message,
        last_run_at=finished_at,
    )
    current_sync_phase_state = _progress.catalog_phase_state(
        state, _constants.CATALOG_SYNC_PHASE
    )
    current_request_creation_phase_state = _progress.catalog_phase_state(
        state,
        _constants.CATALOG_REQUEST_CREATION_PHASE,
    )
    if current_sync_phase_state.get("status") == _constants.CATALOG_PHASE_STATUS_PAUSED:
        sync_phase_state = _progress.replace_catalog_phase_state(
            _constants.CATALOG_SYNC_PHASE,
            current_sync_phase_state,
        )
    else:
        sync_phase_state = _progress.replace_catalog_phase_state(
            _constants.CATALOG_SYNC_PHASE,
            current_sync_phase_state,
            status=_constants.CATALOG_PHASE_STATUS_COMPLETED,
            owner=(
                current_sync_phase_state.get("owner")
                or _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION
            ),
            trigger_source=(
                current_sync_phase_state.get("triggerSource")
                or _progress.sync_trigger_source(state)
            ),
            saved_data={
                **_phase_helpers._phase_saved_data(
                    current_sync_phase_state.get("savedData")
                ),
                "runMode": (
                    current_sync_phase_state.get("owner")
                    or _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION
                ),
                "triggerSource": (
                    current_sync_phase_state.get("triggerSource")
                    or _progress.sync_trigger_source(state)
                ),
            },
            saved_at="",
        )
    request_creation_phase_state = _phase_helpers._catalog_phase_state(
        _constants.CATALOG_REQUEST_CREATION_PHASE,
        status=_constants.CATALOG_PHASE_STATUS_COMPLETED,
        owner=_constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
        trigger_source=(
            current_request_creation_phase_state.get("triggerSource")
            or _progress.sync_trigger_source(state)
        ),
        base_sync_checkpoint_token=(
            current_request_creation_phase_state.get("baseSyncCheckpointToken")
            or _progress.request_creation_base_checkpoint_token(request_creation)
        ),
    )
    phase_states = {
        _constants.CATALOG_SYNC_PHASE: sync_phase_state,
        _constants.CATALOG_REQUEST_CREATION_PHASE: request_creation_phase_state,
    }
    return _progress.persist_catalog_phase_states(
        state,
        phase_states,
        message=(
            f"Automated catalog sync complete. Updated {state.updated_count}, "
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


def advance_catalog_request_creation_once(state):
    request_creation_phase_state = _progress.catalog_phase_state(
        state,
        _constants.CATALOG_REQUEST_CREATION_PHASE,
    )
    request_creation = _progress.catalog_request_creation_progress(state)
    request_creation_base_token = (
        str(request_creation_phase_state.get("baseSyncCheckpointToken") or "").strip()
        or _progress.request_creation_base_checkpoint_token(request_creation)
        or _progress.current_catalog_sync_checkpoint_token(state)
    )
    if not _progress.request_creation_matches_checkpoint(
        request_creation, request_creation_base_token
    ):
        request_creation = {
            "baseCheckpointToken": request_creation_base_token,
            "lastRecordId": "",
            "processedCount": 0,
            "createdCount": 0,
            "unsupportedCount": 0,
        }
    batch = list(
        _completion.catalog_request_creation_queryset(
            after_record_id=str(request_creation.get("lastRecordId") or "").strip()
        )[: _constants.CATALOG_REQUEST_CREATION_BATCH_SIZE]
    )
    if not batch:
        return complete_catalog_automation(state, request_creation=request_creation)

    created_count = int(request_creation.get("createdCount") or 0)
    processed_count = int(request_creation.get("processedCount") or 0)
    unsupported_count = int(request_creation.get("unsupportedCount") or 0)
    last_record_id = str(request_creation.get("lastRecordId") or "").strip()
    for record in batch:
        last_record_id = str(record.id)
        processed_count += 1
        if not _checkpoints.can_process_record_url(record.url):
            unsupported_count += 1
            _constants.logger.warning(
                "Skipping automation request creation for record %s because its URL is unsupported: %s",
                record.id,
                record.url,
            )
            continue
        latest_request = _queries.latest_request_for_record(record)
        if (
            latest_request is None
            and record.book_creation_state == BookCreationState.NOT_CREATED
        ):
            processing_request = _automation_commands.create_request_for_record(
                record,
                origin=SubmissionOrigin.AUTOMATION,
            )
            if processing_request is not None:
                created_count += 1

    next_request_creation = {
        "baseCheckpointToken": request_creation_base_token,
        "lastRecordId": last_record_id,
        "processedCount": processed_count,
        "createdCount": created_count,
        "unsupportedCount": unsupported_count,
    }
    has_more_records = _completion.catalog_request_creation_queryset(
        after_record_id=last_record_id
    ).exists()
    latest_status = _state.persisted_sync_status(state)
    if latest_status == ProcessingSyncStatus.PAUSING:
        if not has_more_records:
            return complete_catalog_automation(
                state, request_creation=next_request_creation
            )
        state.status = ProcessingSyncStatus.PAUSED
        state.progress = _messages.build_catalog_request_creation_progress(
            state,
            request_creation=next_request_creation,
            saved_at=timezone.now().isoformat(),
            trigger_source=_progress.sync_trigger_source(state),
            request_creation_phase_status=_constants.CATALOG_PHASE_STATUS_PAUSED,
            sync_phase_state=_progress.catalog_phase_state(
                state, _constants.CATALOG_SYNC_PHASE
            ),
        )
        state.message = _messages.catalog_request_creation_pause_message(
            next_request_creation
        )
        _messages.update_automation_run_status(
            _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
            state.message,
        )
    elif latest_status != ProcessingSyncStatus.SYNCING:
        return ProcessingSyncState.objects.get(pk=state.pk)
    else:
        if not has_more_records:
            return complete_catalog_automation(
                state, request_creation=next_request_creation
            )
        state.progress = _messages.build_catalog_request_creation_progress(
            state,
            request_creation=next_request_creation,
            trigger_source=_progress.sync_trigger_source(state),
            request_creation_phase_status=_constants.CATALOG_PHASE_STATUS_RUNNING,
            sync_phase_state=_progress.catalog_phase_state(
                state, _constants.CATALOG_SYNC_PHASE
            ),
        )
        state.message = _messages.catalog_request_creation_progress_message(
            next_request_creation
        )
    _checkpoints.save_sync_state(state)
    return state


def __getattr__(name):
    if name in {
        "incomplete_sync_remote_pages",
        "should_use_live_incomplete_fetch",
        "preferred_incomplete_resolution_category",
        "unresolved_incomplete_records_queryset",
        "uses_supported_source_url",
        "incomplete_automation_pages",
    }:
        return getattr(_incomplete_catalog_queries, name)
    raise AttributeError(f"{__name__!r} has no attribute {name!r}")
