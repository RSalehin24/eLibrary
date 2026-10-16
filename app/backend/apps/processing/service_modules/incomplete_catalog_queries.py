"""Incomplete catalog queries."""

import os
import sys

from django.conf import settings
from django.db.models import Q

from ..models import (
    BookRecord,
)
from ..source import normalize_source_url
from . import catalog_phase_helpers as _phase_helpers
from . import checkpoint_and_runtime_adapters as _checkpoints
from . import incomplete_catalog_fetch as _incomplete_fetch
from . import service_imports_and_constants as _constants


def incomplete_automation_pages(page_size=100):
    record_ids = [
        str(record.id)
        for record in unresolved_incomplete_records_queryset()
        .exclude(will_resolve_to_category="")
        .order_by("name", "id")
        .only("id", "category", "was_incomplete")
        if record.was_incomplete
        or _phase_helpers.category_is_incomplete(record.category)
    ]

    pages = []
    for index in range(0, len(record_ids), page_size):
        pages.append(record_ids[index : index + page_size])
    pages.append([])
    return pages


def unresolved_incomplete_records_queryset():
    return BookRecord.objects.filter(resolved_from_incomplete=False).filter(
        Q(was_incomplete=True) | _phase_helpers.incomplete_category_query()
    )


def uses_supported_source_url(url):
    try:
        normalize_source_url(url)
    except ValueError:
        return False
    return True


def should_use_live_incomplete_fetch():
    if not getattr(settings, "PROCESSING_USE_LIVE_SYNC", False):
        return False
    if settings.CELERY_TASK_ALWAYS_EAGER or "pytest" in sys.modules:
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    if not _checkpoints.processing_workers_available():
        return False

    unresolved_urls = list(
        unresolved_incomplete_records_queryset().values_list("url", flat=True)
    )
    return not unresolved_urls or all(
        uses_supported_source_url(url) for url in unresolved_urls
    )


def incomplete_sync_remote_pages():
    if should_use_live_incomplete_fetch():
        try:
            return _incomplete_fetch.fetch_live_incomplete_remote_pages()
        except Exception:
            _constants.logger.warning(
                "Live incomplete catalog fetch failed; falling back to local incomplete snapshot.",
                exc_info=True,
            )
    return incomplete_automation_pages()


def preferred_incomplete_resolution_category(record):
    for candidate in (
        record.will_resolve_to_category,
        _incomplete_fetch.incomplete_resolution_category(
            getattr(record.source_catalog_entry, "raw_data", None),
        ),
        ""
        if _phase_helpers.category_is_incomplete(record.category)
        else record.category,
    ):
        value = str(candidate or "").strip()
        if value and not _phase_helpers.category_is_incomplete(value):
            return value
    return "Uncategorized"
