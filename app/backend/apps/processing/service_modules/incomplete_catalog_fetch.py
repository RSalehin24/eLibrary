from urllib.parse import urljoin
from uuid import uuid4

from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.scraper_support.network import create_session_with_retries
from apps.ingestion.services.resolution import TitleResolver, get_with_host_fallback
from apps.ingestion.services.resolution_support import (
    fetch_source_page_metadata,
    metadata_entry_defaults,
    split_display_title,
    upsert_source_catalog_entry,
)
from bs4 import BeautifulSoup

from ..models import ProcessingSyncStatus
from ..source import normalize_source_url
from . import automation_advancement as _automation
from . import catalog_phase_helpers as _phase_helpers
from . import catalog_progress_state as _progress
from . import catalog_record_sync as _catalog_sync
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import processing_state_queries as _queries
from . import service_imports_and_constants as _constants
from . import state_serializers as _state
from . import sync_runner as _sync_runner
from . import sync_status_messages as _messages


def parse_incomplete_catalog_page(soup):
    entries = []
    seen_urls = set()
    anchors = soup.select(
        ".entry-title a[href], article h2 a[href], article h3 a[href]"
    )

    for anchor in anchors:
        href = urljoin(
            _constants.incomplete_catalog_url(),
            anchor.get("href", ""),
        )
        try:
            normalized_url = normalize_source_url(href)
        except ValueError:
            continue
        if normalized_url in seen_urls:
            continue

        display_title = anchor.get_text(" ", strip=True)
        if not display_title:
            continue

        seen_urls.add(normalized_url)
        title, author_line = split_display_title(display_title)
        entries.append(
            metadata_entry_defaults(
                source_url=normalized_url,
                title=title or display_title,
                author_line=author_line,
                raw_data={
                    "title": title or display_title,
                    "display_title": display_title,
                    "author_line": author_line,
                    "incompleteCategoryUrl": _constants.incomplete_catalog_url(),
                    "metadata_source": "incomplete_archive_page",
                },
            )
        )

    return entries


def incomplete_resolution_category(raw_data, fallback=""):
    raw_data = raw_data if isinstance(raw_data, dict) else {}
    for key in (
        "willResolveToCategory",
        "will_resolve_to_category",
        "resolvedCategory",
        "resolved_category",
        "metadataSourceCategory",
        "category",
        "book_type",
    ):
        value = str(raw_data.get(key) or "").strip()
        if value and not _phase_helpers.category_is_incomplete(value):
            return value
    return str(fallback or "").strip()


def incomplete_remote_payload(stored_entry):
    raw_data = stored_entry.raw_data if isinstance(stored_entry.raw_data, dict) else {}
    return {
        "id": str(stored_entry.id),
        "name": stored_entry.title,
        "url": stored_entry.source_url,
        "category": "অসম্পূর্ণ বই",
        "writer": stored_entry.author_line,
        "translator": raw_data.get("translator") or "",
        "composer": raw_data.get("composer") or "",
        "publisher": raw_data.get("publisher") or "",
        "updatedAt": stored_entry.updated_at.isoformat(),
        "wasIncomplete": True,
        "resolvedFromIncomplete": False,
        "willResolveToCategory": incomplete_resolution_category(raw_data),
    }


def fetch_live_incomplete_page(resolver, page_number):
    response = get_with_host_fallback(
        resolver.session,
        _catalog_sync.incomplete_catalog_page_url(page_number),
        timeout=30,
    )
    try:
        response.raise_for_status()
    except Exception as exc:
        if (
            page_number > 1
            and getattr(getattr(exc, "response", None), "status_code", None) == 404
        ):
            _constants.logger.info(
                "Incomplete catalog page %s returned 404; treating it as the end of the archive.",
                _catalog_sync.incomplete_catalog_page_url(page_number),
            )
            return []
        raise
    entries = parse_incomplete_catalog_page(BeautifulSoup(response.text, "html.parser"))

    normalized_entries = []
    seen_urls = set()
    for entry in entries:
        source_url = entry.get("source_url")
        if not source_url:
            continue

        enriched_entry = dict(entry)
        try:
            metadata = fetch_source_page_metadata(source_url, session=resolver.session)
            resolution_category = incomplete_resolution_category(
                metadata.get("raw_data")
            )
            enriched_entry = {
                **metadata,
                "raw_data": {
                    **(metadata.get("raw_data") or {}),
                    "category": "অসম্পূর্ণ বই",
                    "willResolveToCategory": resolution_category,
                    "metadataSourceCategory": resolution_category,
                    "incompleteCategoryUrl": _constants.incomplete_catalog_url(),
                    "metadata_source": "incomplete_archive_page",
                },
            }
        except Exception:
            _constants.logger.warning(
                "Incomplete metadata enrichment failed for %s; using archive listing metadata.",
                source_url,
                exc_info=True,
            )
            enriched_entry = {
                **entry,
                "raw_data": {
                    **(entry.get("raw_data") or {}),
                    "category": "অসম্পূর্ণ বই",
                    "willResolveToCategory": "",
                    "incompleteCategoryUrl": _constants.incomplete_catalog_url(),
                    "metadata_source": "incomplete_archive_page",
                },
            }

        stored_entry = upsert_source_catalog_entry(enriched_entry)
        payload = incomplete_remote_payload(stored_entry)
        if payload["url"] in seen_urls:
            continue
        seen_urls.add(payload["url"])
        normalized_entries.append(payload)

    return normalized_entries


def fetch_live_incomplete_remote_pages(page_size=100, max_pages=250):
    resolver = TitleResolver(session=create_session_with_retries())
    pages = []
    current_page = []
    seen_urls = set()
    page_signatures = set()

    for page_number in range(1, max_pages + 1):
        page_items = fetch_live_incomplete_page(resolver, page_number)
        if not page_items:
            break

        signature = tuple(item["url"] for item in page_items[:5])
        if signature in page_signatures:
            break
        page_signatures.add(signature)

        deduped_page_items = []
        for item in page_items:
            source_url = item.get("url")
            if not source_url or source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            deduped_page_items.append(item)

        for item in deduped_page_items:
            current_page.append(item)
            if len(current_page) >= page_size:
                pages.append(current_page)
                current_page = []

    if current_page:
        pages.append(current_page)
    pages.append([])
    return pages


def start_sync(
    remote_pages=None,
    *,
    run_mode=_constants.SYNC_RUN_MODE_MANUAL,
    sync_key=None,
    trigger_source=_constants.SYNC_TRIGGER_SOURCE_BUTTON,
):
    sync_key = sync_key or _progress.sync_key_for_run_mode(run_mode)
    live_fetch = False
    session_id = ""
    if run_mode == _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        live_fetch = (
            remote_pages is None and _automation.should_use_live_incomplete_fetch()
        )
        if remote_pages is None or not isinstance(remote_pages, list):
            remote_pages = (
                [] if live_fetch else _automation.incomplete_sync_remote_pages()
            )
    else:
        remote_pages = _queries.catalog_remote_pages(remote_pages)
        live_fetch = _catalog_sync.should_use_live_catalog_fetch(remote_pages, run_mode)
        if not live_fetch and not remote_pages and SourceCatalogEntry.objects.exists():
            remote_pages = _catalog_sync.source_catalog_remote_pages()
        session_id = str(uuid4())

    state = _state.get_sync_state(sync_key)
    preserved_request_creation_phase_state = None
    if sync_key == _constants.PROCESSING_SYNC_KEY_CATALOG:
        current_request_creation_phase_state = _progress.catalog_phase_state(
            state,
            _constants.CATALOG_REQUEST_CREATION_PHASE,
        )
        if (
            current_request_creation_phase_state.get("status")
            == _constants.CATALOG_PHASE_STATUS_PAUSED
        ):
            preserved_request_creation_phase_state = (
                current_request_creation_phase_state
            )
    state.remote_pages = remote_pages
    state.status = ProcessingSyncStatus.SYNCING
    if sync_key == _constants.PROCESSING_SYNC_KEY_CATALOG:
        state.progress = _messages.build_catalog_sync_progress(
            state,
            run_mode,
            live_fetch=live_fetch,
            trigger_source=trigger_source,
            session_id=session_id,
            request_creation_phase_state=preserved_request_creation_phase_state,
        )
    else:
        state.progress = _messages.build_sync_progress(
            run_mode,
            live_fetch=live_fetch,
            trigger_source=trigger_source,
            session_id=session_id,
        )
    state.page_index = 0
    state.fetched_count = 0
    state.skipped_count = 0
    state.updated_count = 0
    state.appended_count = 0
    state.message = _checkpoints.sync_start_message(run_mode)
    state.task_id = ""
    state.queue_name = ""
    state.last_error = ""
    _checkpoints.save_sync_state(state)
    _messages.update_automation_run_status(run_mode, state.message)
    if _checkpoints.should_enqueue_processing_sync_work():
        _catalog_sync.dispatch_sync_task(state, force=True)
    elif _checkpoints.should_run_processing_jobs_inline():
        _sync_runner.run_processing_sync_until_blocked(
            singleton_key=state.singleton_key, task_id=""
        )
    return state
