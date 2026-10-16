from datetime import time as time_type

from apps.ingestion.models import SubmissionOrigin
from django.conf import settings
from django.db import transaction

from ..models import (
    BookCreationRequest,
    BookCreationRequestState,
    BookCreationState,
    BookRecord,
    ProcessingSyncState,
    ProcessingSyncStatus,
)
from . import automation_schedule as _automation_schedule
from . import catalog_progress_state as _progress
from . import catalog_record_sync as _catalog_sync
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import incomplete_catalog_fetch as _incomplete_fetch
from . import processing_state_queries as _queries
from . import request_queue_runtime as _request_queue
from . import service_imports_and_constants as _constants
from . import state_serializers as _state
from . import sync_completion as _completion
from . import sync_lifecycle_actions as _lifecycle
from . import sync_runner as _sync_runner
from . import sync_status_messages as _messages
from . import ui_domain_versions as _ui_versions


def create_request_for_record(
    record, state=BookCreationRequestState.INITIAL, origin=SubmissionOrigin.CURATION
):
    if (
        state == BookCreationRequestState.INITIAL
        and not _checkpoints.can_process_record_url(record.url)
    ):
        _constants.logger.warning(
            "Skipping request creation for record %s because its URL is unsupported: %s",
            record.id,
            record.url,
        )
        return None
    processing_request = BookCreationRequest.objects.create(
        id=_request_queue.next_request_id(_sync_runner.request_id_for_record(record)),
        book_record=record,
        state=state,
        origin=origin,
    )
    _queries.sync_record_state(record)
    domains = _ui_versions.processing_domains_for_request_change(
        None, state, record=record
    )
    if origin == SubmissionOrigin.AUTOMATION:
        domains.update(
            {
                _constants.PROCESSING_CARD_CATALOG_AUTOMATION,
                _constants.PROCESSING_CARD_CREATE_OVERVIEW,
            }
        )
    _ui_versions.publish_processing_ui_domains(domains)
    if state == BookCreationRequestState.INITIAL:
        processing_request = _request_queue.queue_processing_request(processing_request)
    return processing_request


def create_requests_for_record_ids(
    record_ids, *, actor=None, origin=SubmissionOrigin.CURATION
):
    created = []
    for record in BookRecord.objects.filter(pk__in=record_ids).order_by("name", "id"):
        if not _request_queue.record_is_selectable(record):
            continue
        processing_request = create_request_for_record(record, origin=origin)
        if processing_request is not None:
            created.append(processing_request)
    return created


def update_automation_settings(kind, payload):
    automation_settings = _state.get_automation_settings(kind)
    automation_settings.enabled = bool(
        payload.get("enabled", automation_settings.enabled)
    )
    automation_settings.interval = str(
        payload.get("interval") or automation_settings.interval
    )
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
        automation_settings.save(
            update_fields=[
                "enabled",
                "interval",
                "time",
                "saved",
                "status_message",
                "updated_at",
            ]
        )
    else:
        automation_settings.save()
    _ui_versions.publish_processing_ui_domains(
        _ui_versions.processing_domains_for_automation(kind)
    )
    return automation_settings


def run_manual_catalog_sync(
    remote_pages=None,
    *,
    trigger_source=_constants.SYNC_TRIGGER_SOURCE_BUTTON,
):
    sync_state = _state.get_sync_state(_constants.PROCESSING_SYNC_KEY_CATALOG)
    if _state.sync_owner_conflicts(sync_state, _constants.SYNC_RUN_MODE_MANUAL):
        return sync_state
    if (
        sync_state.status == ProcessingSyncStatus.PAUSED
        and _progress.catalog_sync_phase_status(sync_state)
        == _constants.CATALOG_PHASE_STATUS_PAUSED
    ):
        return _lifecycle.resume_sync(
            _constants.PROCESSING_SYNC_KEY_CATALOG,
            run_mode=_constants.SYNC_RUN_MODE_MANUAL,
        )
    if sync_state.status in _constants.SYNC_ACTIVE_STATUSES:
        return sync_state
    return _incomplete_fetch.start_sync(
        remote_pages or None,
        run_mode=_constants.SYNC_RUN_MODE_MANUAL,
        sync_key=_constants.PROCESSING_SYNC_KEY_CATALOG,
        trigger_source=trigger_source,
    )


def run_catalog_automation(*, trigger_source=_constants.SYNC_TRIGGER_SOURCE_BUTTON):
    sync_state = _state.get_sync_state(_constants.PROCESSING_SYNC_KEY_CATALOG)
    if _state.sync_owner_conflicts(
        sync_state, _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION
    ):
        if trigger_source == _constants.SYNC_TRIGGER_SOURCE_SCHEDULER:
            _messages.update_automation_run_status(
                _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
                "Waiting for the catalog runtime to become idle.",
            )
        return sync_state
    if _progress.catalog_request_creation_can_resume(sync_state) or (
        sync_state.status == ProcessingSyncStatus.PAUSED
        and _progress.catalog_sync_phase_status(sync_state)
        == _constants.CATALOG_PHASE_STATUS_PAUSED
    ):
        return _lifecycle.resume_sync(
            _constants.PROCESSING_SYNC_KEY_CATALOG,
            run_mode=_constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
        )
    if sync_state.status in _constants.SYNC_ACTIVE_STATUSES:
        return sync_state
    if (
        _progress.catalog_sync_phase_status(sync_state)
        == _constants.CATALOG_PHASE_STATUS_COMPLETED
        and _progress.catalog_request_creation_phase_status(sync_state)
        == _constants.CATALOG_PHASE_STATUS_NOT_STARTED
    ):
        return _completion.begin_catalog_request_creation(sync_state)
    remote_pages = []
    if _checkpoints.allow_processing_remote_page_payloads():
        remote_pages = _queries.catalog_remote_pages(sync_state.remote_pages)
    if settings.CELERY_TASK_ALWAYS_EAGER and not remote_pages:
        remote_pages = _catalog_sync.source_catalog_remote_pages()
    return _incomplete_fetch.start_sync(
        remote_pages or None,
        run_mode=_constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
        sync_key=_constants.PROCESSING_SYNC_KEY_CATALOG,
        trigger_source=trigger_source,
    )


def run_incomplete_automation(*, trigger_source=_constants.SYNC_TRIGGER_SOURCE_BUTTON):
    sync_state = _state.get_sync_state(_constants.PROCESSING_SYNC_KEY_INCOMPLETE)
    if sync_state.status == ProcessingSyncStatus.PAUSED:
        return _lifecycle.resume_sync(
            _constants.PROCESSING_SYNC_KEY_INCOMPLETE,
            run_mode=_constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
        )
    if sync_state.status in _constants.SYNC_ACTIVE_STATUSES:
        return sync_state
    return _incomplete_fetch.start_sync(
        None,
        run_mode=_constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
        sync_key=_constants.PROCESSING_SYNC_KEY_INCOMPLETE,
        trigger_source=trigger_source,
    )


def reset_processing_data(*, revoke_tasks=False, purge_queue=False):
    task_ids = _request_queue.collect_processing_task_ids() if revoke_tasks else set()
    if task_ids:
        _request_queue.revoke_processing_task_ids(task_ids)

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
        _ui_versions.publish_processing_ui_domains(_constants.PROCESSING_CARD_KEYS)

    if purge_queue:
        _request_queue.purge_processing_task_queue()


PROCESSING_SOURCE_METADATA_CHECKPOINT = "source-metadata"
PROCESSING_SCRAPED_CONTENT_CHECKPOINT = "scraped-content"


def _request_progress(processing_request):
    return (
        processing_request.progress
        if isinstance(processing_request.progress, dict)
        else {}
    )


def __getattr__(name):
    if name in {
        "_local_scheduled_datetime",
        "run_due_processing_automations",
        "automation_is_due",
    }:
        return getattr(_automation_schedule, name)
    raise AttributeError(f"{__name__!r} has no attribute {name!r}")
