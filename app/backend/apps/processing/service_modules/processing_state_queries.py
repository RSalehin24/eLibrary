from types import SimpleNamespace

from apps.catalog.services import find_existing_book_by_source_url
from django.db.models import Prefetch

from ..models import (
    BookCreationRequest,
    BookCreationState,
    BookRecord,
    ProcessingAutomationKind,
)
from ..source import normalize_source_url
from . import remote_record_queries as _remote_record_queries
from . import service_imports_and_constants as _constants
from . import state_serializers as _state
from . import ui_projection_queries as _projections


def processing_state_payload(*, include_lists=True):
    projection_rows = _projections.processing_ui_shared_projection_rows(
        keys=_constants.PROCESSING_SHARED_CARD_KEYS
    )
    versions = _projections.processing_ui_versions_map()
    shared_cards = {
        key: (
            (projection_rows.get(key).payload or {})
            if projection_rows.get(key) is not None
            else _projections.default_processing_shared_projection_payload(key)
        )
        for key in _constants.PROCESSING_SHARED_CARD_KEYS
    }
    summary = {
        "catalog": shared_cards[_constants.PROCESSING_CARD_CATALOG_OVERVIEW].get(
            "summary", {}
        ),
        "notifications": shared_cards[_constants.PROCESSING_CARD_CATALOG_OVERVIEW].get(
            "notifications",
            {},
        ),
        "create": shared_cards[_constants.PROCESSING_CARD_CREATE_OVERVIEW].get(
            "summary", {}
        ),
        "onHold": shared_cards[_constants.PROCESSING_CARD_ON_HOLD_OVERVIEW].get(
            "summary", {}
        ),
        "incomplete": shared_cards[_constants.PROCESSING_CARD_INCOMPLETE_OVERVIEW].get(
            "summary",
            {},
        ),
    }
    automation = {
        "catalog": shared_cards[_constants.PROCESSING_CARD_CATALOG_AUTOMATION].get(
            "automation",
            _state.default_automation_payload(ProcessingAutomationKind.CATALOG),
        ),
        "incomplete": shared_cards[
            _constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION
        ].get(
            "automation",
            _state.default_automation_payload(ProcessingAutomationKind.INCOMPLETE),
        ),
    }
    sync_states = {
        "catalog": shared_cards[_constants.PROCESSING_CARD_CATALOG_SYNC].get(
            "sync",
            _state.default_sync_state_payload(_constants.PROCESSING_SYNC_KEY_CATALOG),
        ),
        "incomplete": shared_cards[
            _constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION
        ].get(
            "sync",
            _state.default_sync_state_payload(
                _constants.PROCESSING_SYNC_KEY_INCOMPLETE
            ),
        ),
    }

    catalog_sync_updated_at = getattr(
        projection_rows.get(_constants.PROCESSING_CARD_CATALOG_SYNC),
        "updated_at",
        None,
    )
    incomplete_sync_updated_at = getattr(
        projection_rows.get(_constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION),
        "updated_at",
        None,
    )
    catalog_sync_version = int(versions.get(_constants.PROCESSING_CARD_CATALOG_SYNC, 0))
    incomplete_sync_version = int(
        versions.get(_constants.PROCESSING_CARD_INCOMPLETE_AUTOMATION, 0)
    )
    catalog_sync_has_activity = _projections.processing_sync_payload_has_activity(
        sync_states["catalog"],
        scope=_constants.PROCESSING_SYNC_KEY_CATALOG,
    )
    incomplete_sync_has_activity = _projections.processing_sync_payload_has_activity(
        sync_states["incomplete"],
        scope=_constants.PROCESSING_SYNC_KEY_INCOMPLETE,
    )
    if _state.sync_is_active_or_paused(SimpleNamespace(**sync_states["incomplete"])):
        primary_sync_payload = sync_states["incomplete"]
    elif _state.sync_is_active_or_paused(SimpleNamespace(**sync_states["catalog"])):
        primary_sync_payload = sync_states["catalog"]
    elif incomplete_sync_has_activity and not catalog_sync_has_activity:
        primary_sync_payload = sync_states["incomplete"]
    elif catalog_sync_has_activity and not incomplete_sync_has_activity:
        primary_sync_payload = sync_states["catalog"]
    elif incomplete_sync_version > catalog_sync_version:
        primary_sync_payload = sync_states["incomplete"]
    elif catalog_sync_version > incomplete_sync_version:
        primary_sync_payload = sync_states["catalog"]
    else:
        if incomplete_sync_updated_at and (
            not catalog_sync_updated_at
            or incomplete_sync_updated_at >= catalog_sync_updated_at
        ):
            primary_sync_payload = sync_states["incomplete"]
        else:
            primary_sync_payload = sync_states["catalog"]
    payload = {
        "summary": summary,
        "sync": primary_sync_payload,
        "syncStates": sync_states,
        "orchestration": {
            "manualPipelineAdvance": False,
        },
        "automation": automation,
        "cards": shared_cards,
        "versions": versions,
    }
    if include_lists:
        payload["records"] = serialized_processing_records()
        payload["requests"] = serialized_processing_requests()
    return payload


def serialized_processing_records():
    from ..serializers import BookRecordSerializer

    return BookRecordSerializer(
        BookRecord.objects.select_related("linked_book")
        .prefetch_related("creation_requests")
        .order_by("name", "id"),
        many=True,
    ).data


def serialized_processing_requests():
    from ..serializers import BookCreationRequestSerializer

    return BookCreationRequestSerializer(
        BookCreationRequest.objects.select_related(
            "book_record",
            "linked_book",
            "book_record__linked_book",
        ).order_by(
            "-updated_at",
            "-created_at",
        ),
        many=True,
    ).data


def processing_request_prefetch():
    return Prefetch(
        "creation_requests",
        queryset=BookCreationRequest.objects.select_related(
            "duplicate_of_request"
        ).order_by(
            "-updated_at",
            "-created_at",
            "id",
        ),
    )


def record_request_list(record):
    cached = getattr(record, "_prefetched_objects_cache", {}).get("creation_requests")
    if cached is not None:
        return list(cached)
    return list(record.creation_requests.order_by("-updated_at", "-created_at", "id"))


def latest_request_for_record(record):
    requests = record_request_list(record)
    return requests[0] if requests else None


def linked_book_for_remote_url(url):
    try:
        normalized_url = normalize_source_url(url)
    except ValueError:
        return None
    return find_existing_book_by_source_url(normalized_url)


def sync_record_state(record):
    latest_request = latest_request_for_record(record)
    if latest_request:
        next_state = latest_request.state
    elif record.linked_book_id:
        next_state = BookCreationState.CREATED
    elif record.book_creation_state not in BookCreationState.values:
        next_state = BookCreationState.NOT_CREATED
    else:
        next_state = record.book_creation_state

    if record.book_creation_state != next_state:
        record.book_creation_state = next_state
        record.save(update_fields=["book_creation_state", "updated_at"])
    return record


def sync_records_for_requests(requests):
    record_ids = {request.book_record_id for request in requests}
    for record in BookRecord.objects.filter(pk__in=record_ids):
        sync_record_state(record)


def __getattr__(name):
    if name in {
        "normalize_remote_record",
        "source_catalog_entry_payload",
        "catalog_remote_pages",
        "is_catalog_remote_page",
    }:
        return getattr(_remote_record_queries, name)
    raise AttributeError(f"{__name__!r} has no attribute {name!r}")
