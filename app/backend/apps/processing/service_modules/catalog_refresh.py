"""Catalog refresh."""

import threading
from concurrent.futures import ThreadPoolExecutor

from apps.ingestion.services.resolution import (
    CATALOG_URL,
    TitleResolver,
    get_with_host_fallback,
)
from apps.ingestion.services.resolution_support import (
    fetch_source_page_metadata,
    upsert_source_catalog_entry,
)
from bs4 import BeautifulSoup
from django.conf import settings

from . import catalog_record_sync as _original
from . import processing_state_queries as _queries
from . import service_imports_and_constants as _constants


def refresh_catalog_parallel(concurrency=None):
    from apps.ingestion.pipeline.scraper_support.network import (
        create_session_with_retries,
    )

    if concurrency is None:
        concurrency = getattr(settings, "CELERY_PROCESSING_CONCURRENCY", 5)

    stop_flag = threading.Event()
    page_lock = threading.Lock()
    seen_lock = threading.Lock()
    count_lock = threading.Lock()
    next_page = 1
    seen_urls = set()
    total_appended = 0
    total_updated = 0

    def worker():
        nonlocal next_page, total_appended, total_updated

        while not stop_flag.is_set():
            with page_lock:
                if stop_flag.is_set():
                    return
                page_number = next_page
                next_page += 1

            session = create_session_with_retries()
            resolver = TitleResolver(session=session)

            try:
                response = get_with_host_fallback(
                    resolver.session,
                    CATALOG_URL,
                    params=resolver.archive_query_params(page_number=page_number),
                    timeout=30,
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                entries = resolver.parse_catalog_page(soup)
            except Exception:
                _constants.logger.exception("Catalog page refresh failed.")
                continue

            if not entries:
                stop_flag.set()
                return

            local_appended = 0
            local_updated = 0
            for entry in entries:
                if stop_flag.is_set():
                    return

                with seen_lock:
                    if entry["source_url"] in seen_urls:
                        continue
                    seen_urls.add(entry["source_url"])

                try:
                    metadata = fetch_source_page_metadata(
                        entry["source_url"], session=session
                    )
                    stored_entry = upsert_source_catalog_entry(metadata)
                    payload = _queries.source_catalog_entry_payload(stored_entry)
                    result = _original.upsert_remote_records([payload])
                    local_appended += result["appended_count"]
                    local_updated += result["updated_count"]
                except Exception:
                    _constants.logger.exception("Catalog entry refresh failed.")
                    continue

            with count_lock:
                total_appended += local_appended
                total_updated += local_updated

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        for future in futures:
            future.result()

    return {
        "appended_count": total_appended,
        "updated_count": total_updated,
        "total": total_appended + total_updated,
    }
