import os
import sys
from urllib.parse import urljoin
from uuid import uuid4

from apps.common.identifiers import is_valid_uuid_string
from apps.ingestion.models import SourceCatalogEntry
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q

from ..models import BookCreationState, BookRecord
from . import catalog_refresh as _catalog_refresh
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import processing_state_queries as _queries
from . import service_imports_and_constants as _constants
from . import state_serializers as _state
from . import sync_runner as _sync_runner
from . import ui_domain_versions as _ui_versions


def upsert_remote_records(records):
    skipped_count = 0
    updated_count = 0
    appended_count = 0
    published_domains = set()

    for raw_record in records:
        data = _queries.normalize_remote_record(raw_record)
        if not data["url"]:
            continue

        source_entry_filters = Q(source_url=data["url"])
        if is_valid_uuid_string(data["id"]):
            source_entry_filters |= Q(pk=data["id"])
        source_entry = (
            SourceCatalogEntry.objects.filter(source_entry_filters)
            .order_by("-updated_at")
            .first()
        )
        linked_book = _queries.linked_book_for_remote_url(data["url"])
        desired_state = (
            data["bookCreationState"]
            if data["bookCreationState"] in BookCreationState.values
            else BookCreationState.CREATED
            if linked_book
            else BookCreationState.NOT_CREATED
        )
        defaults = {
            "name": data["name"],
            "url": data["url"],
            "category": data["category"],
            "writer": data["writer"],
            "translator": data["translator"],
            "composer": data["composer"],
            "publisher": data["publisher"],
            "book_creation_state": desired_state,
            "linked_book": linked_book,
            "source_catalog_entry": source_entry,
            "was_incomplete": data["wasIncomplete"],
            "resolved_from_incomplete": data["resolvedFromIncomplete"],
            "will_resolve_to_category": data["willResolveToCategory"],
        }

        record = (
            BookRecord.objects.select_related("linked_book")
            .filter(Q(pk=data["id"]) | Q(url=data["url"]))
            .order_by("id")
            .first()
        )
        before_snapshot = _state.processing_record_snapshot(record)
        if record is None:
            preferred_id = data["id"] or None
            create_kwargs = dict(defaults)
            if preferred_id and not BookRecord.objects.filter(pk=preferred_id).exists():
                create_kwargs["id"] = preferred_id
            try:
                record = BookRecord.objects.create(**create_kwargs)
                _queries.sync_record_state(record)
                published_domains.update(
                    _ui_versions.processing_domains_for_record_change(
                        None,
                        _state.processing_record_snapshot(record),
                    )
                )
                appended_count += 1
                continue
            except IntegrityError:
                record = (
                    BookRecord.objects.select_related("linked_book")
                    .filter(Q(pk=data["id"]) | Q(url=data["url"]))
                    .order_by("id")
                    .first()
                )
                if record is None:
                    raise

        changed_fields = [
            field_name
            for field_name, value in defaults.items()
            if getattr(record, field_name) != value
        ]
        if changed_fields:
            for field_name in changed_fields:
                setattr(record, field_name, defaults[field_name])
            record.save(update_fields=[*changed_fields, "updated_at"])
            updated_count += 1
        else:
            skipped_count += 1

        _queries.sync_record_state(record)
        after_snapshot = _state.processing_record_snapshot(record)
        if before_snapshot != after_snapshot:
            published_domains.update(
                _ui_versions.processing_domains_for_record_change(
                    before_snapshot,
                    after_snapshot,
                )
            )

    if published_domains:
        _ui_versions.publish_processing_ui_domains(published_domains)
    return {
        "skipped_count": skipped_count,
        "updated_count": updated_count,
        "appended_count": appended_count,
    }


def source_catalog_remote_pages(page_size=100):
    entries = SourceCatalogEntry.objects.order_by("title", "id")
    pages = []
    current_page = []
    for entry in entries.iterator(chunk_size=page_size):
        current_page.append(_queries.source_catalog_entry_payload(entry))
        if len(current_page) >= page_size:
            pages.append(current_page)
            current_page = []
    if current_page:
        pages.append(current_page)
    pages.append([])
    return pages


def reconcile_remote_pages(remote_pages):
    remote_pages = remote_pages if isinstance(remote_pages, list) else []
    fetched_count = 0
    skipped_count = 0
    updated_count = 0
    appended_count = 0
    page_index = 0
    completed = False

    for page_index, page in enumerate(remote_pages):
        if not page:
            completed = True
            break

        result = upsert_remote_records(page)
        fetched_count += len(page)
        skipped_count += result["skipped_count"]
        updated_count += result["updated_count"]
        appended_count += result["appended_count"]

    if remote_pages and not completed:
        page_index = len(remote_pages)

    return {
        "fetched_count": fetched_count,
        "skipped_count": skipped_count,
        "updated_count": updated_count,
        "appended_count": appended_count,
        "page_index": page_index,
        "completed": completed or not remote_pages,
    }


def should_use_live_catalog_fetch(remote_pages, run_mode):
    return (
        bool(getattr(settings, "PROCESSING_USE_LIVE_SYNC", False))
        and not settings.CELERY_TASK_ALWAYS_EAGER
        and "pytest" not in sys.modules
        and not os.environ.get("PYTEST_CURRENT_TEST")
        and not remote_pages
        and run_mode
        in {
            _constants.SYNC_RUN_MODE_MANUAL,
            _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
        }
        and _checkpoints.processing_workers_available()
    )


def dispatch_sync_task(sync_state, *, force=False):
    from ..tasks import run_processing_sync_task

    sync_state.refresh_from_db(fields=["status", "task_id", "queue_name", "updated_at"])
    if sync_state.status not in _constants.SYNC_ACTIVE_STATUSES:
        return sync_state
    if not force and sync_state.task_id:
        return sync_state

    assigned_task_id = str(uuid4())
    sync_state.task_id = assigned_task_id
    sync_state.queue_name = _constants.PROCESSING_TASK_QUEUE
    sync_state.last_error = ""
    _checkpoints.save_sync_state(
        sync_state,
        update_fields=["task_id", "queue_name", "last_error", "updated_at"],
    )

    try:
        async_result = run_processing_sync_task.apply_async(
            args=[sync_state.singleton_key],
            task_id=assigned_task_id,
            queue=_constants.PROCESSING_TASK_QUEUE,
        )
        dispatched_task_id = (
            getattr(async_result, "id", assigned_task_id) or assigned_task_id
        )
        if dispatched_task_id != assigned_task_id:
            sync_state.task_id = dispatched_task_id
            _checkpoints.save_sync_state(
                sync_state, update_fields=["task_id", "updated_at"]
            )
    except Exception as exc:
        _constants.logger.warning(
            "Processing sync task dispatch failed.", exc_info=True
        )
        sync_state.task_id = ""
        sync_state.queue_name = "inline-fallback"
        sync_state.last_error = str(exc)
        _checkpoints.save_sync_state(
            sync_state,
            update_fields=["task_id", "queue_name", "last_error", "updated_at"],
        )
        _sync_runner.run_processing_sync_until_blocked(
            singleton_key=sync_state.singleton_key,
            task_id="",
        )
    return sync_state


def incomplete_catalog_page_url(page_number):
    if page_number <= 1:
        return _constants.incomplete_catalog_url()
    return urljoin(_constants.incomplete_catalog_url(), f"page/{page_number}/")


def __getattr__(name):
    if name in {"refresh_catalog_parallel"}:
        return getattr(_catalog_refresh, name)
    raise AttributeError(f"{__name__!r} has no attribute {name!r}")
