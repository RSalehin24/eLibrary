from apps.catalog.models import BookGroup

from ..models import BookCreationRequest, BookCreationRequestState
from . import maintenance_and_request_actions as _maintenance
from . import processing_state_queries as _queries
from . import request_pipeline_tick as _request_pipeline_tick
from . import request_processing_persistence as _persistence
from . import request_queue_runtime as _request_queue
from . import state_serializers as _state
from . import ui_domain_versions as _ui_versions


def _resolve_existing_duplicate_book(processing_request):
    """Return the existing Book this processing_request is duplicating, or None."""
    candidates = []
    target_request = processing_request.duplicate_of_request
    if target_request is not None:
        candidates.append(getattr(target_request, "linked_book", None))
    target_record = processing_request.duplicate_of_record
    if target_record is not None:
        candidates.append(getattr(target_record, "linked_book", None))
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def _ensure_book_group_for_existing(existing_book):
    """Return (and lazily create) the BookGroup linking sibling editions."""
    if existing_book.group_id:
        return existing_book.group
    canonical_title = (existing_book.title or "").strip() or "Untitled"
    group = BookGroup.objects.create(canonical_title=canonical_title)
    existing_book.group = group
    existing_book.save(update_fields=["group", "updated_at"])
    return group


def apply_new_edition_action(processing_request, *, actor=None):
    """Phase E: treat as a new book that is a sibling edition of the existing
    duplicate. Wires both books to a shared BookGroup and re-queues the
    submission for full creation.
    """
    processing_request = _persistence._reload_processing_request(processing_request.id)

    existing_book = _resolve_existing_duplicate_book(processing_request)
    group = _ensure_book_group_for_existing(existing_book) if existing_book else None

    submission = getattr(processing_request, "submission", None)
    if submission is not None and group is not None:
        payload = dict(submission.raw_payload or {})
        payload["target_book_group_id"] = str(group.id)
        submission.raw_payload = payload
        submission.save(update_fields=["raw_payload", "updated_at"])

    return apply_new_action(processing_request, actor=actor)


def apply_new_action(processing_request, *, actor=None):
    processing_request = _persistence._reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    record_before = _state.processing_record_snapshot(processing_request.book_record)
    processing_request.state = BookCreationRequestState.INITIAL
    processing_request.is_confirmed_not_duplicate = True
    processing_request.force_generate = False
    processing_request.duplicate_confirmed = False
    processing_request.duplicate_of_request = None
    processing_request.duplicate_of_record = None
    processing_request.linked_book = None
    processing_request.error_message = ""
    processing_request.progress = None
    processing_request.save(
        update_fields=[
            "state",
            "is_confirmed_not_duplicate",
            "force_generate",
            "duplicate_confirmed",
            "duplicate_of_request",
            "duplicate_of_record",
            "linked_book",
            "error_message",
            "progress",
            "updated_at",
        ]
    )
    record = processing_request.book_record
    record.linked_book = None
    record.is_duplicate = False
    record.duplicate_of_record = None
    record.save(
        update_fields=[
            "linked_book",
            "is_duplicate",
            "duplicate_of_record",
            "updated_at",
        ]
    )
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


def apply_confirm_duplicate_action(processing_request):
    processing_request = _persistence._reload_processing_request(processing_request.id)
    record_before = _state.processing_record_snapshot(processing_request.book_record)
    target_request = processing_request.duplicate_of_request
    if processing_request.duplicate_of_record_id and not target_request:
        target_request = (
            BookCreationRequest.objects.filter(
                book_record_id=processing_request.duplicate_of_record_id
            )
            .exclude(pk=processing_request.pk)
            .order_by("-updated_at", "-created_at")
            .first()
        )
    processing_request.state = BookCreationRequestState.DUPLICATE
    processing_request.duplicate_confirmed = True
    if target_request:
        processing_request.duplicate_of_request = target_request
        processing_request.duplicate_of_record = target_request.book_record
    processing_request.save(
        update_fields=[
            "state",
            "duplicate_confirmed",
            "duplicate_of_request",
            "duplicate_of_record",
            "updated_at",
        ]
    )

    if processing_request.duplicate_of_record_id:
        processing_request.book_record.is_duplicate = True
        processing_request.book_record.duplicate_of_record = (
            processing_request.duplicate_of_record
        )
        processing_request.book_record.save(
            update_fields=["is_duplicate", "duplicate_of_record", "updated_at"]
        )
    _queries.sync_record_state(processing_request.book_record)
    _ui_versions.publish_processing_ui_domains(
        _ui_versions.processing_domains_for_request_change(
            BookCreationRequestState.DUPLICATE,
            BookCreationRequestState.DUPLICATE,
            record=processing_request.book_record,
        )
        | _ui_versions.processing_domains_for_record_change(
            record_before,
            _state.processing_record_snapshot(processing_request.book_record),
            current_request_state=BookCreationRequestState.DUPLICATE,
        )
    )
    return processing_request


def apply_recreate_action(processing_request, *, actor=None):
    processing_request = _persistence._reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    record_before = _state.processing_record_snapshot(processing_request.book_record)
    processing_request.state = BookCreationRequestState.INITIAL
    processing_request.force_generate = False
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


def apply_request_action(request_ids, action, *, delete_book=False, actor=None):
    requests = list(
        BookCreationRequest.objects.filter(pk__in=request_ids)
        .select_related("book_record", "linked_book")
        .order_by("created_at", "id")
    )
    changed = []
    for processing_request in requests:
        if action == "delete":
            _maintenance.apply_delete_action(
                processing_request, delete_book=delete_book
            )
        elif action == "pause":
            _maintenance.apply_pause_action(processing_request)
        elif action == "resume":
            _maintenance.apply_resume_action(processing_request, actor=actor)
        elif action == "retry":
            _maintenance.apply_retry_action(processing_request, actor=actor)
        elif action == "force_generate":
            _maintenance.apply_force_generate_action(processing_request, actor=actor)
        elif action == "new":
            apply_new_action(processing_request, actor=actor)
        elif action == "new_edition":
            apply_new_edition_action(processing_request, actor=actor)
        elif action == "confirm_duplicate":
            apply_confirm_duplicate_action(processing_request)
        elif action in {"create_again", "recreate"}:
            apply_recreate_action(processing_request, actor=actor)
        else:
            continue
        changed.append(processing_request)
    _queries.sync_records_for_requests(changed)
    return changed


def __getattr__(name):
    if name in {"advance_pipeline_once"}:
        return getattr(_request_pipeline_tick, name)
    raise AttributeError(f"{__name__!r} has no attribute {name!r}")
