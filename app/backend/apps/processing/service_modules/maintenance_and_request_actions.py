from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.pipeline.book_manifest import disambiguate_duplicate_content_paths
from apps.ingestion.pipeline.curated_validation import (
    SOURCE_CHROME_BLOCK_TAGS,
    SOURCE_CHROME_PATTERNS,
    is_source_chrome_block,
)
from bs4 import BeautifulSoup
from django.utils import timezone

from ..models import (
    BookCreationRequest,
    BookCreationRequestState,
    ProcessingSyncState,
    ProcessingSyncStatus,
)
from . import automation_commands as _automation_commands
from . import catalog_progress_state as _progress
from . import catalog_record_sync as _catalog_sync
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import processing_state_queries as _queries
from . import request_action_dispatch as _actions
from . import request_processing_persistence as _persistence
from . import request_processing_pipeline as _pipeline
from . import request_queue_runtime as _request_queue
from . import service_imports_and_constants as _constants
from . import state_serializers as _state
from . import sync_runner as _sync_runner
from . import sync_status_messages as _messages
from . import ui_domain_versions as _ui_versions


def repair_self_linked_duplicate_requests():
    repaired = []
    published_domains = set()
    queryset = (
        BookCreationRequest.objects.filter(
            state=BookCreationRequestState.DUPLICATE,
            linked_book__isnull=False,
            linked_book__deleted_at__isnull=True,
            duplicate_of_request__isnull=True,
            duplicate_of_record__isnull=True,
        )
        .select_related("book_record", "linked_book", "book_record__linked_book")
        .order_by("created_at", "id")
    )

    for processing_request in queryset:
        previous_state = processing_request.state
        record_before = _state.processing_record_snapshot(
            processing_request.book_record
        )
        current_book = _request_queue.processing_linked_book(
            processing_request.book_record,
            processing_request,
        )
        if current_book is None or current_book.id != processing_request.linked_book_id:
            continue

        processing_request.state = BookCreationRequestState.CREATED
        processing_request.progress = None
        processing_request.error_message = ""
        processing_request.duplicate_confirmed = False
        processing_request.save(
            update_fields=[
                "state",
                "progress",
                "error_message",
                "duplicate_confirmed",
                "updated_at",
            ]
        )

        record = processing_request.book_record
        record_update_fields = []
        if record.linked_book_id != current_book.id:
            record.linked_book = current_book
            record_update_fields.append("linked_book")
        if record.is_duplicate:
            record.is_duplicate = False
            record_update_fields.append("is_duplicate")
        if record.duplicate_of_record_id:
            record.duplicate_of_record = None
            record_update_fields.append("duplicate_of_record")
        if record_update_fields:
            record.save(update_fields=[*record_update_fields, "updated_at"])

        _queries.sync_record_state(record)
        repaired.append(processing_request)
        published_domains.update(
            _ui_versions.processing_domains_for_request_change(
                previous_state,
                BookCreationRequestState.CREATED,
                record=record,
            )
            | _ui_versions.processing_domains_for_record_change(
                record_before,
                _state.processing_record_snapshot(record),
                current_request_state=BookCreationRequestState.CREATED,
            )
        )

    if published_domains:
        _ui_versions.publish_processing_ui_domains(published_domains)
    return repaired


def mark_stale_processing_requests():
    cutoff = timezone.now() - _constants.PROCESSING_STALE_AFTER
    stale_requests = list(
        BookCreationRequest.objects.filter(
            state=BookCreationRequestState.PROCESSING,
            updated_at__lt=cutoff,
        ).select_related("book_record")
    )
    recovered = []
    for processing_request in stale_requests:
        recovered_request = _pipeline._transition_request_state(
            processing_request.id,
            BookCreationRequestState.PROCESSING,
            BookCreationRequestState.QUEUED,
        )
        recovered_request.error_message = ""
        recovered_request.is_resumed = True
        recovered_request.save(
            update_fields=["error_message", "is_resumed", "updated_at"]
        )
        recovered.append(recovered_request)
        _request_queue.queue_processing_request(recovered_request)
    return recovered


def recover_stale_sync_states():
    cutoff = timezone.now() - _constants.PROCESSING_STALE_AFTER
    states = list(
        ProcessingSyncState.objects.filter(
            status__in=_constants.SYNC_ACTIVE_STATUSES,
            updated_at__lt=cutoff,
        ).order_by("singleton_key")
    )
    recovered = []
    for state in states:
        run_mode = _progress.sync_run_mode(state)
        if state.status == ProcessingSyncStatus.PAUSING:
            if (
                state.singleton_key == _constants.PROCESSING_SYNC_KEY_CATALOG
                and _progress.sync_phase(state)
                == _constants.CATALOG_REQUEST_CREATION_PHASE
            ):
                state.progress = _messages.build_catalog_request_creation_progress(
                    state,
                    request_creation=_progress.catalog_request_creation_progress(state)
                    or _progress.initial_catalog_request_creation_progress(state),
                    run_mode=run_mode,
                    trigger_source=_progress.sync_trigger_source(state),
                    request_creation_phase_status=_constants.CATALOG_PHASE_STATUS_PAUSED,
                    sync_phase_state=_progress.catalog_phase_state(
                        state, _constants.CATALOG_SYNC_PHASE
                    ),
                )
            elif state.singleton_key == _constants.PROCESSING_SYNC_KEY_CATALOG:
                state.progress = _messages.build_catalog_sync_progress(
                    state,
                    run_mode,
                    next_page_index=state.page_index,
                    fetched_count=state.fetched_count,
                    saved_at=timezone.now().isoformat(),
                    live_fetch=_checkpoints.sync_uses_live_fetch(state),
                    trigger_source=_progress.sync_trigger_source(state),
                    sync_phase_status=_constants.CATALOG_PHASE_STATUS_PAUSED,
                    request_creation_phase_state=_progress.catalog_phase_state(
                        state,
                        _constants.CATALOG_REQUEST_CREATION_PHASE,
                    ),
                )
            else:
                state.progress = _messages.build_sync_progress(
                    run_mode,
                    next_page_index=state.page_index,
                    fetched_count=state.fetched_count,
                    saved_at=timezone.now().isoformat(),
                    live_fetch=_checkpoints.sync_uses_live_fetch(state),
                    trigger_source=_progress.sync_trigger_source(state),
                )
            state.status = ProcessingSyncStatus.PAUSED
            state.message = f"{_checkpoints.sync_run_label(run_mode)} progress saved after interruption."
        else:
            state.message = f"Recovering interrupted {_checkpoints.sync_run_label(run_mode).lower()}."
        state.task_id = ""
        state.queue_name = ""
        _checkpoints.save_sync_state(
            state,
            update_fields=[
                "status",
                "progress",
                "task_id",
                "queue_name",
                "message",
                "updated_at",
            ],
        )
        if (
            state.status == ProcessingSyncStatus.SYNCING
            and _checkpoints.should_enqueue_processing_sync_work()
        ):
            _catalog_sync.dispatch_sync_task(state, force=True)
        recovered.append(state)
    return recovered


def run_processing_maintenance():
    recovered = mark_stale_processing_requests()
    recovered_sync = recover_stale_sync_states()
    repaired = repair_self_linked_duplicate_requests()
    return {
        "recoveredCount": len(recovered),
        "syncRecoveredCount": len(recovered_sync),
        "repairedCount": len(repaired),
    }


def run_processing_runtime_tick():
    sync_results = {}
    for sync_key in (
        _constants.PROCESSING_SYNC_KEY_CATALOG,
        _constants.PROCESSING_SYNC_KEY_INCOMPLETE,
    ):
        state = _state.get_sync_state(sync_key)
        if state.status in _constants.SYNC_ACTIVE_STATUSES:
            sync_results[sync_key] = _checkpoints.sync_state_task_payload(
                _sync_runner.advance_sync_once(sync_key)
            )
    return {
        "sync": sync_results,
        "advancedCount": _actions.advance_pipeline_once(),
    }


def apply_delete_action(processing_request, *, delete_book=False):
    processing_request = _persistence._reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    if (
        delete_book
        and processing_request.linked_book
        and processing_request.linked_book.deleted_at is None
    ):
        processing_request.linked_book.soft_delete()

    processing_request.state = BookCreationRequestState.DELETED
    processing_request.progress = None
    processing_request.error_message = ""
    processing_request.save(
        update_fields=["state", "progress", "error_message", "updated_at"]
    )
    _queries.sync_record_state(processing_request.book_record)
    _ui_versions.publish_processing_ui_domains(
        _ui_versions.processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.DELETED,
            record=processing_request.book_record,
        )
    )
    return processing_request


def apply_pause_action(processing_request):
    processing_request = _persistence._reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    saved_data = _persistence._request_saved_data(processing_request)
    processing_request.state = BookCreationRequestState.PAUSED
    processing_request.progress = _persistence._build_processing_progress(
        _automation_commands._request_progress(processing_request).get("checkpoint")
        or "Pause requested",
        saved_data,
    )
    processing_request.error_message = ""
    processing_request.save(
        update_fields=["state", "progress", "error_message", "updated_at"]
    )
    _queries.sync_record_state(processing_request.book_record)
    _ui_versions.publish_processing_ui_domains(
        _ui_versions.processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.PAUSED,
            record=processing_request.book_record,
        )
    )
    return processing_request


def apply_resume_action(processing_request, *, actor=None):
    processing_request = _persistence._reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    processing_request.state = BookCreationRequestState.INITIAL
    processing_request.is_resumed = True
    processing_request.force_generate = False
    processing_request.error_message = ""
    processing_request.save(
        update_fields=[
            "state",
            "is_resumed",
            "force_generate",
            "error_message",
            "updated_at",
        ]
    )
    _queries.sync_record_state(processing_request.book_record)
    _ui_versions.publish_processing_ui_domains(
        _ui_versions.processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.INITIAL,
            record=processing_request.book_record,
        )
    )
    _request_queue.queue_processing_request(processing_request)
    return processing_request


_REVIEW_REQUIRED_ERROR_MSG = "Curated document requires review before asset generation."


def _strip_source_chrome_from_document(document):
    """Return a copy of *document* with source-chrome blocks removed from BODY sections.

    Looks for blocks matching SOURCE_CHROME_PATTERNS inside each BODY section's
    HTML and removes them.  Returns (cleaned_document, stripped_count).
    """
    from apps.catalog.models import CuratedSectionType

    sections = document.get("sections") or []
    cleaned_sections = []
    total_stripped = 0
    for section in sections:
        if section.get("section_type") != CuratedSectionType.BODY:
            cleaned_sections.append(section)
            continue
        html = section.get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        stripped = 0
        for block in soup.find_all(SOURCE_CHROME_BLOCK_TAGS):
            block_text = clean_display_text(block.get_text(" ", strip=True))
            normalized = normalize_catalog_text(block_text)
            for pattern in SOURCE_CHROME_PATTERNS:
                normalized_pattern = normalize_catalog_text(pattern)
                if normalized_pattern and is_source_chrome_block(
                    normalized, normalized_pattern, pattern
                ):
                    block.decompose()
                    stripped += 1
                    break
        if stripped:
            total_stripped += stripped
            cleaned_sections.append({**section, "html": str(soup)})
        else:
            cleaned_sections.append(section)
    if total_stripped:
        return {**document, "sections": cleaned_sections}, total_stripped
    return document, 0


def _fix_duplicate_paths_in_document(document):
    """Return a copy of *document* with duplicate content paths disambiguated.

    Uses the existing ``disambiguate_duplicate_content_paths`` function which
    handles two cases: genuinely distinct chapters sharing a title (renamed with
    an occurrence suffix) and inline-extraction artefacts (duplicates merged by
    keeping the richest body).  Returns (fixed_document, fixed_count).
    """
    toc = document.get("toc") or []
    content_items = document.get("content_items") or []

    from apps.ingestion.pipeline.curated_validation import duplicate_paths as _dp

    dupes = _dp(content_items)
    if not dupes:
        return document, 0

    fixed_toc, fixed_items = disambiguate_duplicate_content_paths(toc, content_items)
    fixed_count = len(content_items) - len(fixed_items) + len(dupes)
    return {**document, "toc": fixed_toc, "content_items": fixed_items}, max(
        fixed_count, len(dupes)
    )


def apply_force_generate_action(processing_request, *, actor=None):
    """Re-queue a failed request through the full pipeline with the force flag set.

    Unlike a plain retry, force-generate marks the request so the pipeline will
    bypass the ``REVIEW_REQUIRED`` gate and apply automatic mitigations
    (source-chrome stripping + duplicate content-path disambiguation) before
    generating assets. The request moves back onto the Requests queue and the
    book is recreated from scratch (re-scrape → curate → mitigate → export).
    """
    processing_request = _persistence._reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    record_before = _state.processing_record_snapshot(processing_request.book_record)
    processing_request.state = BookCreationRequestState.INITIAL
    processing_request.force_generate = True
    processing_request.progress = None
    processing_request.error_message = ""
    processing_request.duplicate_confirmed = False
    processing_request.save(
        update_fields=[
            "state",
            "force_generate",
            "progress",
            "error_message",
            "duplicate_confirmed",
            "updated_at",
        ]
    )
    record = processing_request.book_record
    if record.is_duplicate or record.duplicate_of_record_id:
        record.is_duplicate = False
        record.duplicate_of_record = None
        record.save(update_fields=["is_duplicate", "duplicate_of_record", "updated_at"])
    _queries.sync_record_state(record)
    _ui_versions.publish_processing_ui_domains(
        _ui_versions.processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.INITIAL,
            record=record,
        )
        | _ui_versions.processing_domains_for_record_change(
            record_before,
            _state.processing_record_snapshot(record),
            current_request_state=BookCreationRequestState.INITIAL,
        )
    )
    _request_queue.queue_processing_request(processing_request)
    return processing_request


def apply_retry_action(processing_request, *, actor=None):
    processing_request = _persistence._reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    record_before = _state.processing_record_snapshot(processing_request.book_record)
    processing_request.state = BookCreationRequestState.INITIAL
    processing_request.force_generate = False
    processing_request.error_message = ""
    processing_request.progress = None
    processing_request.duplicate_confirmed = False
    processing_request.save(
        update_fields=[
            "state",
            "force_generate",
            "error_message",
            "progress",
            "duplicate_confirmed",
            "updated_at",
        ]
    )
    record = processing_request.book_record
    if record.is_duplicate or record.duplicate_of_record_id:
        record.is_duplicate = False
        record.duplicate_of_record = None
        record.save(update_fields=["is_duplicate", "duplicate_of_record", "updated_at"])
    _queries.sync_record_state(record)
    _ui_versions.publish_processing_ui_domains(
        _ui_versions.processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.INITIAL,
            record=record,
        )
        | _ui_versions.processing_domains_for_record_change(
            record_before,
            _state.processing_record_snapshot(record),
            current_request_state=BookCreationRequestState.INITIAL,
        )
    )
    _request_queue.queue_processing_request(processing_request)
    return processing_request
