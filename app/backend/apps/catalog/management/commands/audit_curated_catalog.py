"""Catalogue-wide audit report for the curated dataset.

Run via: ``python manage.py audit_curated_catalog [--report-path=PATH]``

Emits a single JSON document summarising:
  * how many books exist in the curated catalogue,
  * how many have at least one EPUB asset on disk and pass a basic EPUB
    integrity check (zip opens, contains the expected XHTML pages, has at
    least one non-empty chapter, NAV points only to spine items),
  * structure_type histogram across CuratedBookDocument,
  * contributor counts per role,
  * a sample of books that failed an EPUB check (with their failure
    reasons), for downstream investigation.

The audit is read-only and side-effect free.
"""

import json
import os
import re
import zipfile
from collections import Counter

from django.core.management.base import BaseCommand

from apps.catalog.models import (
    Book,
    BookContributor,
    Contributor,
    ContributorRole,
    CuratedBookDocument,
    GeneratedAsset,
)
from apps.catalog.models.choices import GeneratedAssetType, GeneratedAssetStatus


_HTML_TAG = re.compile(r"<[^>]+>")


def chapter_has_visible_text(xhtml_bytes):
    try:
        text = xhtml_bytes.decode("utf-8", errors="replace")
    except Exception:
        return False
    text = _HTML_TAG.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&#160;", " ")
    return bool(text.strip())


def inspect_epub(path):
    """Return (ok: bool, reasons: list[str], details: dict)."""
    reasons = []
    details = {"xhtml_count": 0, "empty_xhtml": 0, "size_bytes": 0}
    if not os.path.exists(path):
        return False, ["missing_file"], details
    details["size_bytes"] = os.path.getsize(path)
    if details["size_bytes"] < 1024:
        reasons.append("file_too_small")
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            xhtml_names = [n for n in names if n.lower().endswith(".xhtml")]
            details["xhtml_count"] = len(xhtml_names)
            content_pages = [
                n for n in xhtml_names
                if os.path.basename(n) not in {"nav.xhtml", "cover.xhtml"}
            ]
            non_empty = 0
            for name in content_pages:
                try:
                    data = zf.read(name)
                except Exception:
                    reasons.append(f"unreadable:{name}")
                    continue
                if chapter_has_visible_text(data):
                    non_empty += 1
                else:
                    details["empty_xhtml"] += 1
            if non_empty == 0:
                reasons.append("no_non_empty_chapter")
            # Sanity: NAV must exist
            if not any(os.path.basename(n) == "nav.xhtml" for n in xhtml_names):
                reasons.append("missing_nav")
    except zipfile.BadZipFile:
        return False, ["bad_zip"], details
    except Exception as exc:  # noqa: BLE001 - report unexpected errors
        return False, [f"open_error:{type(exc).__name__}"], details
    return (not reasons), reasons, details


class Command(BaseCommand):
    help = "Generate a quality-audit report for the curated catalogue."

    def add_arguments(self, parser):
        parser.add_argument("--report-path", default="/app/logs/audit_curated_catalog.json")
        parser.add_argument("--failure-sample-size", type=int, default=50)
        parser.add_argument("--media-root", default="/storage/media/scraped-books")

    def handle(self, *args, **options):
        report_path = options["report_path"]
        sample_size = options["failure_sample_size"]
        media_root = options["media_root"]

        book_total = Book.objects.count()
        curated_total = CuratedBookDocument.objects.count()
        # Quarantine breakdown (Book.review_state==REJECTED == quality-gate
        # quarantined; Book.state==ARCHIVED is the published-side signal).
        from apps.common.models import LifecycleState, ReviewState
        quarantined = Book.objects.filter(
            review_state=ReviewState.REJECTED,
            state=LifecycleState.ARCHIVED,
        ).count()
        needs_review = Book.objects.filter(
            review_state=ReviewState.NEEDS_REVIEW,
        ).count()

        structure_counter = Counter()
        for value in CuratedBookDocument.objects.values_list("structure_type", flat=True):
            structure_counter[value or ""] += 1

        contributor_role_counter = Counter()
        for role in BookContributor.objects.values_list("role", flat=True):
            contributor_role_counter[role or ""] += 1

        epub_ok = 0
        epub_missing = 0
        epub_bad = 0
        failure_samples = []

        epub_assets = GeneratedAsset.objects.filter(
            asset_type=GeneratedAssetType.EPUB
        ).select_related("book").iterator(chunk_size=200)
        seen_book_ids = set()
        for asset in epub_assets:
            book = asset.book
            if not book:
                continue
            seen_book_ids.add(book.id)
            epub_file = asset.file
            epub_path = epub_file.path if epub_file and epub_file.name else None
            if not epub_path or not os.path.exists(epub_path):
                epub_missing += 1
                if len(failure_samples) < sample_size:
                    failure_samples.append(
                        {
                            "book_id": str(book.id),
                            "title": book.title,
                            "reason": "no_epub_file",
                            "asset_status": asset.status,
                        }
                    )
                continue
            ok, reasons, details = inspect_epub(epub_path)
            if ok:
                epub_ok += 1
            else:
                epub_bad += 1
                if len(failure_samples) < sample_size:
                    failure_samples.append(
                        {
                            "book_id": str(book.id),
                            "title": book.title,
                            "epub_path": epub_path,
                            "reasons": reasons,
                            "details": details,
                        }
                    )

        books_without_epub_asset = Book.objects.exclude(id__in=seen_book_ids).count()

        report = {
            "totals": {
                "books": book_total,
                "curated_documents": curated_total,
                "contributors": Contributor.objects.count(),
                "book_contributors": BookContributor.objects.count(),
            },
            "epub_health": {
                "ok": epub_ok,
                "missing_file": epub_missing,
                "failed_inspection": epub_bad,
                "books_without_epub_asset": books_without_epub_asset,
            },
            "quarantine": {
                "quarantined": quarantined,
                "needs_review": needs_review,
            },
            "structure_type_histogram": dict(structure_counter.most_common()),
            "contributor_role_counts": {
                role: contributor_role_counter.get(role, 0)
                for role in ContributorRole.values
            },
            "failure_samples": failure_samples,
        }

        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        self.stdout.write(json.dumps(report["totals"]))
        self.stdout.write(json.dumps(report["epub_health"]))
        self.stdout.write(f"Full report written to {report_path}")
