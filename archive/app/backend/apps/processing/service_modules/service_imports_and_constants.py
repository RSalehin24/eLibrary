import json
import logging
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta, time as time_type
from time import monotonic
from types import SimpleNamespace
from urllib.parse import unquote, urljoin, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup
from config.celery import app as celery_app
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import (
    Case,
    CharField,
    F,
    IntegerField,
    Max,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from kombu import Queue
from redis import Redis
from redis.exceptions import RedisError

from apps.catalog.services import find_existing_book_by_source_url
from apps.catalog.models import BookGroup, CuratedDocumentStatus
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.models import SourceCatalogEntry, SubmissionOrigin
from apps.ingestion.pipeline.scraper_support.network import create_session_with_retries
from apps.ingestion.pipeline.curated_pipeline import curate_scraped_book_data
from apps.ingestion.pipeline.curated_export import curated_document_with_projection
from apps.ingestion.pipeline.curated_validation import (
    SOURCE_CHROME_BLOCK_TAGS,
    SOURCE_CHROME_CONTAINS_PATTERNS,
    SOURCE_CHROME_MAX_BLOCK_LENGTH,
    SOURCE_CHROME_PATTERNS,
    is_source_chrome_block,
    source_chrome_hits,
)
from apps.ingestion.pipeline.book_manifest import disambiguate_duplicate_content_paths
from apps.ingestion.services.normalization import promote_leading_front_matter
from apps.ingestion.services.resolution import CATALOG_URL, TitleResolver, get_with_host_fallback
from apps.ingestion.services.resolution_support import (
    fetch_source_page_metadata,
    metadata_entry_defaults,
    split_display_title,
    upsert_source_catalog_entry,
)
from apps.ingestion.services.submissions_support.persistence import export_payload_from_book

from .models import (
    BookCreationRequest,
    BookCreationRequestState,
    BookCreationState,
    BookRecord,
    ProcessingAutomationKind,
    ProcessingAutomationSettings,
    ProcessingUiDomainVersion,
    ProcessingUiProjection,
    ProcessingSyncState,
    ProcessingSyncStatus,
)
from .source import (
    capture_source_page_metadata,
    curate_book,
    detect_metadata_duplicate,
    find_exact_existing_book,
    generate_exports,
    normalize_source_url,
    persist_curated_book,
    persist_scraped_book,
    scrape_book,
    sync_assets,
)


logger = logging.getLogger(__name__)

SYNC_RUN_MODE_MANUAL = "manual"
SYNC_RUN_MODE_CATALOG_AUTOMATION = "catalog_automation"
SYNC_RUN_MODE_INCOMPLETE_AUTOMATION = "incomplete_automation"
SYNC_TRIGGER_SOURCE_BUTTON = "button"
SYNC_TRIGGER_SOURCE_SCHEDULER = "scheduler"
PROCESSING_SYNC_KEY_CATALOG = "catalog"
PROCESSING_SYNC_KEY_INCOMPLETE = "incomplete"
CATALOG_SYNC_PHASE = "sync"
CATALOG_REQUEST_CREATION_PHASE = "request_creation"
CATALOG_PHASE_STATUS_NOT_STARTED = "not_started"
CATALOG_PHASE_STATUS_RUNNING = "running"
CATALOG_PHASE_STATUS_PAUSING = "pausing"
CATALOG_PHASE_STATUS_PAUSED = "paused"
CATALOG_PHASE_STATUS_COMPLETED = "completed"
CATALOG_PHASE_STATUSES = {
    CATALOG_PHASE_STATUS_NOT_STARTED,
    CATALOG_PHASE_STATUS_RUNNING,
    CATALOG_PHASE_STATUS_PAUSING,
    CATALOG_PHASE_STATUS_PAUSED,
    CATALOG_PHASE_STATUS_COMPLETED,
}
CATALOG_REQUEST_CREATION_BATCH_SIZE = 50
INCOMPLETE_CATEGORY_KEYWORDS = (
    "incomplete",
    "unfinished",
    "অসম্পূর্ণ",
    "অসম্পূর্ণ বই",
)
INCOMPLETE_CATALOG_URL = (
    "https://{}/genres/"
    "%E0%A6%85%E0%A6%B8%E0%A6%AE%E0%A6%AA%E0%A7%82%E0%A6%B0%E0%A7%8D%E0%A6%A3-"
    "%E0%A6%AC%E0%A6%87/"
).format(getattr(settings, "SOURCE_SITE_HOST", "") or "")
TERMINAL_STATES = {
    BookCreationRequestState.CREATED,
    BookCreationRequestState.FAILED,
    BookCreationRequestState.DUPLICATE,
    BookCreationRequestState.DELETED,
}
ACTIVE_STATES = {
    BookCreationRequestState.INITIAL,
    BookCreationRequestState.QUEUED,
    BookCreationRequestState.PROCESSING,
}
SYNC_ACTIVE_STATUSES = {
    ProcessingSyncStatus.SYNCING,
    ProcessingSyncStatus.PAUSING,
}
PROCESSING_STALE_AFTER = timedelta(minutes=20)
PROCESSING_STALE_MESSAGE = "Processing exceeded 20 minutes without completing."
PROCESSING_DISPATCH_STALE_AFTER = timedelta(minutes=2)
PROCESSING_SCRAPE_HEARTBEAT_INTERVAL = 300  # seconds between heartbeat DB touches
MAX_PROCESSING_REQUEST_ATTEMPTS = 3
DEFAULT_AUTOMATION_INTERVAL = "weekly"
DEFAULT_AUTOMATION_TIME = time_type(3, 0)
LEGACY_AUTOMATION_STATUS_MESSAGE = "Not configured."
PROCESSING_TASK_QUEUE = "processing"
PROCESSING_WORKER_CACHE_SECONDS = 2
PROCESSING_DISPATCH_REQUESTED_AT_KEY = "_dispatchRequestedAt"
PROCESSING_DISPATCH_TASK_ID_KEY = "_dispatchTaskId"
PROCESSING_SYNC_CHECKPOINT_KEY_PREFIX = "processing:sync-checkpoint"
PROCESSING_TABLE_DEFAULT_LIMIT = 60
PROCESSING_TABLE_MAX_LIMIT = 600
PROCESSING_CARD_CATALOG_OVERVIEW = "catalog-overview"
PROCESSING_CARD_CATALOG_SYNC = "catalog-sync"
PROCESSING_CARD_CATALOG_AUTOMATION = "catalog-automation"
PROCESSING_CARD_CREATE_OVERVIEW = "create-overview"
PROCESSING_CARD_ON_HOLD_OVERVIEW = "on-hold-overview"
PROCESSING_CARD_INCOMPLETE_OVERVIEW = "incomplete-overview"
PROCESSING_CARD_INCOMPLETE_AUTOMATION = "incomplete-automation"
PROCESSING_CARD_CATALOG_RECORDS = "catalog-records"
PROCESSING_CARD_INCOMPLETE_RECORDS = "incomplete-records"
PROCESSING_CARD_INCOMPLETE_COMPLETED = "incomplete-completed"
PROCESSING_CARD_MULTIPAGE_RECORDS = "multipage-records"
PROCESSING_PAGE_KEY_MULTIPAGE = "multipage"
PROCESSING_CARD_EMPTY_CHAPTERS_RECORDS = "empty-chapters-records"
PROCESSING_PAGE_KEY_EMPTY_CHAPTERS = "empty-chapters"

PROCESSING_REQUEST_CARD_STATES = {
    "create-requests": {BookCreationRequestState.INITIAL},
    "create-queue": {BookCreationRequestState.QUEUED},
    "create-processing": {BookCreationRequestState.PROCESSING},
    "create-created": {BookCreationRequestState.CREATED},
    "on-hold-paused": {BookCreationRequestState.PAUSED},
    "on-hold-failed": {BookCreationRequestState.FAILED},
    "on-hold-duplicate": {BookCreationRequestState.DUPLICATE},
    "on-hold-deleted": {BookCreationRequestState.DELETED},
}

PROCESSING_SHARED_CARD_KEYS = {
    PROCESSING_CARD_CATALOG_OVERVIEW,
    PROCESSING_CARD_CATALOG_SYNC,
    PROCESSING_CARD_CATALOG_AUTOMATION,
    PROCESSING_CARD_CREATE_OVERVIEW,
    PROCESSING_CARD_ON_HOLD_OVERVIEW,
    PROCESSING_CARD_INCOMPLETE_OVERVIEW,
    PROCESSING_CARD_INCOMPLETE_AUTOMATION,
}
PROCESSING_SHARED_PROJECTION_DEPENDENCIES = {
    PROCESSING_CARD_CATALOG_OVERVIEW: {PROCESSING_CARD_CATALOG_OVERVIEW},
    PROCESSING_CARD_CATALOG_SYNC: {
        PROCESSING_CARD_CATALOG_SYNC,
        PROCESSING_CARD_CATALOG_AUTOMATION,
    },
    PROCESSING_CARD_CATALOG_AUTOMATION: {PROCESSING_CARD_CATALOG_AUTOMATION},
    PROCESSING_CARD_CREATE_OVERVIEW: {PROCESSING_CARD_CREATE_OVERVIEW},
    PROCESSING_CARD_ON_HOLD_OVERVIEW: {PROCESSING_CARD_ON_HOLD_OVERVIEW},
    PROCESSING_CARD_INCOMPLETE_OVERVIEW: {PROCESSING_CARD_INCOMPLETE_OVERVIEW},
    PROCESSING_CARD_INCOMPLETE_AUTOMATION: {PROCESSING_CARD_INCOMPLETE_AUTOMATION},
}
PROCESSING_TABLE_CARD_KEYS = {
    PROCESSING_CARD_CATALOG_RECORDS,
    PROCESSING_CARD_INCOMPLETE_RECORDS,
    PROCESSING_CARD_INCOMPLETE_COMPLETED,
    PROCESSING_CARD_MULTIPAGE_RECORDS,
    PROCESSING_CARD_EMPTY_CHAPTERS_RECORDS,
    *PROCESSING_REQUEST_CARD_STATES.keys(),
}
PROCESSING_CARD_KEYS = [
    PROCESSING_CARD_CATALOG_OVERVIEW,
    PROCESSING_CARD_CATALOG_SYNC,
    PROCESSING_CARD_CATALOG_AUTOMATION,
    PROCESSING_CARD_CATALOG_RECORDS,
    PROCESSING_CARD_CREATE_OVERVIEW,
    "create-requests",
    "create-queue",
    "create-processing",
    "create-created",
    PROCESSING_CARD_ON_HOLD_OVERVIEW,
    "on-hold-paused",
    "on-hold-failed",
    "on-hold-duplicate",
    "on-hold-deleted",
    PROCESSING_CARD_INCOMPLETE_OVERVIEW,
    PROCESSING_CARD_INCOMPLETE_AUTOMATION,
    PROCESSING_CARD_INCOMPLETE_RECORDS,
    PROCESSING_CARD_INCOMPLETE_COMPLETED,
    PROCESSING_CARD_MULTIPAGE_RECORDS,
    PROCESSING_CARD_EMPTY_CHAPTERS_RECORDS,
]
PROCESSING_PAGE_DOMAINS = {
    PROCESSING_SYNC_KEY_CATALOG: {
        PROCESSING_CARD_CATALOG_OVERVIEW,
        PROCESSING_CARD_CATALOG_SYNC,
        PROCESSING_CARD_CATALOG_AUTOMATION,
        PROCESSING_CARD_CATALOG_RECORDS,
    },
    "create": {
        PROCESSING_CARD_CREATE_OVERVIEW,
        "create-requests",
        "create-queue",
        "create-processing",
        "create-created",
    },
    "on-hold": {
        PROCESSING_CARD_ON_HOLD_OVERVIEW,
        "on-hold-paused",
        "on-hold-failed",
        "on-hold-duplicate",
        "on-hold-deleted",
    },
    PROCESSING_SYNC_KEY_INCOMPLETE: {
        PROCESSING_CARD_INCOMPLETE_OVERVIEW,
        PROCESSING_CARD_INCOMPLETE_AUTOMATION,
        PROCESSING_CARD_INCOMPLETE_RECORDS,
        PROCESSING_CARD_INCOMPLETE_COMPLETED,
    },
    PROCESSING_PAGE_KEY_MULTIPAGE: {
        PROCESSING_CARD_MULTIPAGE_RECORDS,
    },
    PROCESSING_PAGE_KEY_EMPTY_CHAPTERS: {
        PROCESSING_CARD_EMPTY_CHAPTERS_RECORDS,
    },
}
PROCESSING_STATE_REQUEST_GROUP = {
    BookCreationRequestState.INITIAL,
    BookCreationRequestState.QUEUED,
    BookCreationRequestState.PROCESSING,
    BookCreationRequestState.CREATED,
}
PROCESSING_STATE_ON_HOLD_GROUP = {
    BookCreationRequestState.PAUSED,
    BookCreationRequestState.FAILED,
    BookCreationRequestState.DUPLICATE,
    BookCreationRequestState.DELETED,
}

PROCESSING_WORKER_AVAILABILITY = {
    "checked_at": 0.0,
    "available": None,
}
PROCESSING_UI_VERSION_COLLECTOR = ContextVar(
    "processing_ui_version_collector",
    default=None,
)
