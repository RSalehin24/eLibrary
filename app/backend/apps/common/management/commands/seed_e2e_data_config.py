from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.access.models import (
    Bookmark,
    PermissionGrant,
    PermissionScope,
    ReadingSession,
)
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookSource,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.catalog.models.choices import ContributorRole
from apps.catalog.services import replace_book_relations
from apps.common.epub_utils import build_simple_epub
from apps.common.models import LifecycleState
from apps.common.text import normalize_catalog_text
from apps.ingestion.models import (
    BookSubmission,
    CatalogAutomationSettings,
    CatalogCurationMode,
    CatalogCurationRun,
    CatalogCurationTrigger,
    JobStatus,
    JobType,
    ProcessingJob,
    ProcessingLog,
    ResolutionStatus,
    SourceCatalogEntry,
    SourceCatalogRefreshState,
    SourceCatalogRefreshStatus,
    SubmissionInputType,
    SubmissionOrigin,
    SubmissionStatus,
)

E2E_TITLE_PREFIX = "E2E "
E2E_EMAIL_DOMAIN = "@e2e.local"
E2E_SOURCE_PREFIX = "https://www.example.com/books/e2e-"
DEFAULT_WRITER = "E2E Writer"
DEFAULT_CATEGORY = "E2E Fiction"
DEFAULT_SERIES = "E2E Starter Series"
INCOMPLETE_CATEGORY = "অসম্পূর্ণ বই"


@dataclass(frozen=True)
class SeedBook:
    title: str
    source_url: str
    with_assets: bool = False
    categories: tuple[str, ...] = (DEFAULT_CATEGORY,)
    series: tuple[str, ...] = (DEFAULT_SERIES,)


BOOK_DEFINITIONS = {
    "home_primary": SeedBook(
        title="E2E Home Library Book",
        source_url=f"{E2E_SOURCE_PREFIX}home-library-book/",
    ),
    "home_secondary": SeedBook(
        title="E2E Search Companion Book",
        source_url=f"{E2E_SOURCE_PREFIX}search-companion-book/",
    ),
    "detail": SeedBook(
        title="E2E Detail Book",
        source_url=f"{E2E_SOURCE_PREFIX}detail-book/",
        with_assets=True,
    ),
    "preview": SeedBook(
        title="E2E Preview Book",
        source_url=f"{E2E_SOURCE_PREFIX}preview-book/",
        with_assets=True,
    ),
    "access": SeedBook(
        title="E2E Access Grant Book",
        source_url=f"{E2E_SOURCE_PREFIX}access-grant-book/",
    ),
    "incomplete": SeedBook(
        title="E2E Incomplete Catalog Book",
        source_url=f"{E2E_SOURCE_PREFIX}incomplete-catalog-book/",
        categories=(INCOMPLETE_CATEGORY,),
    ),
}

SUBMISSION_TITLES = (
    "E2E Alpha Submission",
    "E2E Beta Submission",
)

CATALOG_ENTRIES = (
    {
        "title": "000 E2E Alpha Catalog Book",
        "source_url": f"{E2E_SOURCE_PREFIX}alpha-catalog-book/",
        "author_line": DEFAULT_WRITER,
        "category": DEFAULT_CATEGORY,
    },
    {
        "title": "001 E2E Beta Catalog Book",
        "source_url": f"{E2E_SOURCE_PREFIX}beta-catalog-book/",
        "author_line": DEFAULT_WRITER,
        "category": DEFAULT_CATEGORY,
    },
    {
        "title": "002 E2E Incomplete Catalog Book",
        "source_url": f"{E2E_SOURCE_PREFIX}incomplete-catalog-book/",
        "author_line": DEFAULT_WRITER,
        "category": INCOMPLETE_CATEGORY,
    },
)

ACCESS_USER_EMAIL = f"access-manager{E2E_EMAIL_DOMAIN}"
ACCESS_USER_PASSWORD = "E2E-access-pass-123"

PROCESSING_SUBMISSION_TITLES = {
    "user_pending": "E2E User Pending Submission",
    "user_processing": "E2E User Processing Submission",
    "user_stopped": "E2E User Stopped Submission",
    "user_deleted": "E2E User Deleted Submission",
    "user_failed": "E2E User Failed Submission",
    "automation_pending": "E2E Automation Pending Submission",
    "automation_ready": "E2E Automation Ready Submission",
    "automation_processing": "E2E Automation Processing Submission",
    "automation_queued": "E2E Automation Queued Submission",
    "automation_stopped": "E2E Automation Stopped Submission",
    "automation_deleted": "E2E Automation Deleted Submission",
    "curation_ready": "E2E Curation Ready Submission",
    "curation_processing": "E2E Curation Processing Submission",
    "curation_queued": "E2E Curation Queued Submission",
    "curation_stopped": "E2E Curation Stopped Submission",
    "curation_deleted": "E2E Curation Deleted Submission",
    "duplicate_review": "E2E Duplicate Review Submission",
}

FAILED_LOG_MESSAGE = "Seeded failed job log entry."

SCHEDULED_RUN_ACTIVE_SUMMARY = {
    "queued_creates": 7,
    "queued_updates": 1,
    "skipped_ready": 2,
}

SCHEDULED_RUN_FAILED_SUMMARY = {
    "queued_creates": 2,
    "queued_updates": 3,
    "skipped_ready": 4,
}


def seed_source_url(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return f"{E2E_SOURCE_PREFIX}{slug}/"


__all__ = [
    "ACCESS_USER_EMAIL",
    "ACCESS_USER_PASSWORD",
    "BOOK_DEFINITIONS",
    "CATALOG_ENTRIES",
    "DEFAULT_CATEGORY",
    "DEFAULT_SERIES",
    "DEFAULT_WRITER",
    "E2E_EMAIL_DOMAIN",
    "E2E_SOURCE_PREFIX",
    "E2E_TITLE_PREFIX",
    "FAILED_LOG_MESSAGE",
    "INCOMPLETE_CATEGORY",
    "PROCESSING_SUBMISSION_TITLES",
    "SCHEDULED_RUN_ACTIVE_SUMMARY",
    "SCHEDULED_RUN_FAILED_SUMMARY",
    "SUBMISSION_TITLES",
    "BaseCommand",
    "Book",
    "BookSource",
    "BookSubmission",
    "Bookmark",
    "CatalogAutomationSettings",
    "CatalogCurationMode",
    "CatalogCurationRun",
    "CatalogCurationTrigger",
    "CommandError",
    "ContentFile",
    "ContributorRole",
    "GeneratedAsset",
    "GeneratedAssetStatus",
    "GeneratedAssetType",
    "JobStatus",
    "JobType",
    "LifecycleState",
    "Path",
    "PermissionGrant",
    "PermissionScope",
    "ProcessingJob",
    "ProcessingLog",
    "Q",
    "ReadingSession",
    "ResolutionStatus",
    "SeedBook",
    "SourceCatalogEntry",
    "SourceCatalogRefreshState",
    "SourceCatalogRefreshStatus",
    "SubmissionInputType",
    "SubmissionOrigin",
    "SubmissionStatus",
    "User",
    "annotations",
    "build_simple_epub",
    "cache",
    "call_command",
    "dataclass",
    "normalize_catalog_text",
    "re",
    "replace_book_relations",
    "seed_source_url",
    "settings",
    "time",
    "transaction",
]
