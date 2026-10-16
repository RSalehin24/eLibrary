"""Historical transport and model exports for compatibility callers."""

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
from datetime import time as time_type
from datetime import timedelta
from time import monotonic
from types import SimpleNamespace
from urllib.parse import unquote, urljoin, urlparse
from uuid import uuid4

from apps.catalog.models import BookGroup, CuratedDocumentStatus
from apps.catalog.services import find_existing_book_by_source_url
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.models import SourceCatalogEntry, SubmissionOrigin
from apps.ingestion.pipeline.book_manifest import disambiguate_duplicate_content_paths
from apps.ingestion.pipeline.curated_export import curated_document_with_projection
from apps.ingestion.pipeline.curated_pipeline import curate_scraped_book_data
from apps.ingestion.pipeline.curated_validation import (
    SOURCE_CHROME_BLOCK_TAGS,
    SOURCE_CHROME_CONTAINS_PATTERNS,
    SOURCE_CHROME_MAX_BLOCK_LENGTH,
    SOURCE_CHROME_PATTERNS,
    is_source_chrome_block,
    source_chrome_hits,
)
from apps.ingestion.pipeline.scraper_support.network import create_session_with_retries
from apps.ingestion.services.normalization import promote_leading_front_matter
from apps.ingestion.services.resolution import (
    CATALOG_URL,
    TitleResolver,
    get_with_host_fallback,
)
from apps.ingestion.services.resolution_support import (
    fetch_source_page_metadata,
    metadata_entry_defaults,
    split_display_title,
    upsert_source_catalog_entry,
)
from apps.ingestion.services.submissions_support.persistence import (
    export_payload_from_book,
)
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
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from kombu import Queue
from redis import Redis
from redis.exceptions import RedisError

from ..models import (
    BookCreationRequest,
    BookCreationRequestState,
    BookCreationState,
    BookRecord,
    ProcessingAutomationKind,
    ProcessingAutomationSettings,
    ProcessingSyncState,
    ProcessingSyncStatus,
    ProcessingUiDomainVersion,
    ProcessingUiProjection,
)
from ..source import (
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

__all__ = [
    "CATALOG_URL",
    "SOURCE_CHROME_BLOCK_TAGS",
    "SOURCE_CHROME_CONTAINS_PATTERNS",
    "SOURCE_CHROME_MAX_BLOCK_LENGTH",
    "SOURCE_CHROME_PATTERNS",
    "BeautifulSoup",
    "BookCreationRequest",
    "BookCreationRequestState",
    "BookCreationState",
    "BookGroup",
    "BookRecord",
    "Case",
    "CharField",
    "Coalesce",
    "ContextVar",
    "CuratedDocumentStatus",
    "F",
    "IntegerField",
    "IntegrityError",
    "Max",
    "OuterRef",
    "Prefetch",
    "ProcessingAutomationKind",
    "ProcessingAutomationSettings",
    "ProcessingSyncState",
    "ProcessingSyncStatus",
    "ProcessingUiDomainVersion",
    "ProcessingUiProjection",
    "Q",
    "Queue",
    "Redis",
    "RedisError",
    "SimpleNamespace",
    "SourceCatalogEntry",
    "SubmissionOrigin",
    "Subquery",
    "ThreadPoolExecutor",
    "TitleResolver",
    "Value",
    "When",
    "capture_source_page_metadata",
    "celery_app",
    "clean_display_text",
    "contextmanager",
    "create_session_with_retries",
    "curate_book",
    "curate_scraped_book_data",
    "curated_document_with_projection",
    "detect_metadata_duplicate",
    "disambiguate_duplicate_content_paths",
    "export_payload_from_book",
    "fetch_source_page_metadata",
    "find_exact_existing_book",
    "find_existing_book_by_source_url",
    "generate_exports",
    "get_with_host_fallback",
    "is_source_chrome_block",
    "json",
    "logging",
    "metadata_entry_defaults",
    "monotonic",
    "normalize_catalog_text",
    "normalize_source_url",
    "os",
    "parse_datetime",
    "persist_curated_book",
    "persist_scraped_book",
    "promote_leading_front_matter",
    "scrape_book",
    "settings",
    "source_chrome_hits",
    "split_display_title",
    "sync_assets",
    "sys",
    "threading",
    "time",
    "time_type",
    "timedelta",
    "timezone",
    "transaction",
    "unquote",
    "upsert_source_catalog_entry",
    "urljoin",
    "urlparse",
    "uuid",
    "uuid4",
]
