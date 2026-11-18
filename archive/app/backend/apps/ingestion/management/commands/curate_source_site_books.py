import gc
import json
import traceback
from collections import Counter
from contextlib import nullcontext
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, reset_queries, transaction

from apps.catalog.models import CuratedBookDocument, CuratedDocumentStatus
from apps.catalog.services import find_existing_book_by_source_url
from apps.common.models import LifecycleState, ReviewState
from apps.common.text import clean_display_text, normalize_catalog_text
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline.curated_persistence import (
    persist_curated_book,
    persist_curated_document,
)
from apps.ingestion.pipeline.curated_validation import validate_document
from apps.ingestion.pipeline.curated_pipeline import curate_book_document
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.ingestion.services.normalization import plain_text_from_html
from apps.ingestion.services.curation_support.quality_gate import book_quality_gate
from apps.ingestion.services.legacy_adapter import generate_exports
from apps.ingestion.services.resolution import TitleResolver
from apps.ingestion.services.submissions import sync_assets


def path_tuple(value):
    if isinstance(value, (list, tuple)):
        return tuple(clean_display_text(part) for part in value if clean_display_text(part))
    return ()


def unique_content_paths(content_items):
    seen = set()
    duplicates = []
    for item in content_items or []:
        path = path_tuple(item.get("path")) or (clean_display_text(item.get("title", "")),)
        if path in seen:
            duplicates.append(" / ".join(path))
        seen.add(path)
    return duplicates


def comparable_text(value):
    if isinstance(value, (list, tuple)):
        value = ", ".join(clean_display_text(item) for item in value if clean_display_text(item))
    return clean_display_text(value)


def normalized_matches_expected(expected, actual):
    expected_normalized = normalize_catalog_text(expected)
    actual_normalized = normalize_catalog_text(actual)
    if not expected_normalized:
        return True
    if not actual_normalized:
        return False
    return (
        expected_normalized == actual_normalized
        or expected_normalized in actual_normalized
        or actual_normalized in expected_normalized
    )


def raw_data_value(entry, *keys):
    raw_data = entry.raw_data if isinstance(entry.raw_data, dict) else {}
    for key in keys:
        value = clean_display_text(raw_data.get(key, ""))
        if value:
            return value
    return ""


def catalog_mismatch_errors(curated, catalog_entry):
    if catalog_entry is None:
        return []

    projection = curated.get("projection") or {}
    errors = []

    expected_title = clean_display_text(catalog_entry.title)
    actual_title = comparable_text(projection.get("book_title", ""))
    if expected_title and not actual_title:
        errors.append(f"Catalog title was not extracted: expected {expected_title}.")
    elif expected_title and normalize_catalog_text(expected_title) != normalize_catalog_text(actual_title):
        errors.append(f"Catalog title mismatch: expected {expected_title}; extracted {actual_title}.")

    expected_author = clean_display_text(catalog_entry.author_line) or raw_data_value(
        catalog_entry,
        "author_line",
        "meta_author_line",
        "title_author_line",
    )
    actual_author = comparable_text(projection.get("author", ""))
    if expected_author and not normalized_matches_expected(expected_author, actual_author):
        errors.append(f"Catalog author mismatch: expected {expected_author}; extracted {actual_author or 'empty'}.")

    expected_series = raw_data_value(catalog_entry, "series")
    actual_series = comparable_text(projection.get("series", ""))
    if expected_series and not normalized_matches_expected(expected_series, actual_series):
        errors.append(f"Catalog series mismatch: expected {expected_series}; extracted {actual_series or 'empty'}.")

    expected_category = raw_data_value(catalog_entry, "category")
    actual_category = comparable_text(projection.get("book_type", ""))
    if expected_category and not normalized_matches_expected(expected_category, actual_category):
        errors.append(f"Catalog category mismatch: expected {expected_category}; extracted {actual_category or 'empty'}.")

    return errors


def verify_curated_result(curated, *, book=None, curated_document=None):
    document = curated.get("document") or {}
    projection = curated.get("projection") or {}
    snapshot = curated.get("source_snapshot") or {}
    validation = document.get("validation") or {}
    errors = []

    recomputed = validate_document(document, {**snapshot, "raw_scrape_payload": projection})
    if recomputed.get("status") != document.get("status"):
        errors.append(
            "Validation status changed on recompute: "
            f"{document.get('status')} -> {recomputed.get('status')}."
        )
    if recomputed.get("errors") != validation.get("errors", []):
        errors.append("Validation errors changed on recompute.")

    title = clean_display_text(projection.get("book_title", ""))
    if not title:
        errors.append("Projection is missing book_title.")
    if not document.get("structure_type"):
        errors.append("Document is missing structure_type.")

    content_items = projection.get("content_items") or []
    main_content = projection.get("main_content", "")
    body_sections = [
        section
        for section in document.get("sections", [])
        if section.get("section_type") == "body"
        and plain_text_from_html(section.get("html", ""))
    ]
    if not content_items and not plain_text_from_html(main_content):
        errors.append("Projection has no content_items or main_content.")
    if not body_sections:
        errors.append("Document has no text-bearing body sections.")
    for duplicate_path in unique_content_paths(content_items):
        errors.append(f"Duplicate projected content path: {duplicate_path}.")

    if document.get("status") == CuratedDocumentStatus.VALIDATED and validation.get("errors"):
        errors.append("Validated document still has validation errors.")

    if book is None or curated_document is None:
        return errors

    if clean_display_text(book.title) != title:
        errors.append("Persisted book title does not match projection.")
    if book.main_content_html != main_content:
        errors.append("Persisted main content does not match projection.")
    if book.toc != (projection.get("toc") or []):
        errors.append("Persisted TOC does not match projection.")
    if book.content_items != content_items:
        errors.append("Persisted content_items do not match projection.")

    content_summary = (book.raw_scrape_payload or {}).get("content_summary") or {}
    if content_summary.get("content_item_count") != len(content_items):
        errors.append("Persisted content summary has wrong content_item_count.")
    if content_summary.get("content_html_chars") != sum(
        len(item.get("content", ""))
        for item in content_items
        if isinstance(item, dict)
    ):
        errors.append("Persisted content summary has wrong content_html_chars.")

    if curated_document.status != document.get("status"):
        errors.append("Curated document status does not match in-memory document.")
    if curated_document.structure_type != document.get("structure_type", ""):
        errors.append("Curated document structure_type does not match in-memory document.")
    if curated_document.sections.count() != len(document.get("sections") or []):
        errors.append("Persisted curated section count does not match document.")
    if curated_document.entities.count() != len(document.get("entities") or []):
        errors.append("Persisted curated entity count does not match document.")
    if curated_document.evidence.count() != len(document.get("evidence") or []):
        errors.append("Persisted curated evidence count does not match document.")

    return errors


class Command(BaseCommand):
    help = "Curate source site books into evidence-backed documents in resumable batches."

    def add_arguments(self, parser):
        parser.add_argument("--source-url", action="append", default=[])
        parser.add_argument("--discover", action="store_true")
        parser.add_argument("--max-pages", type=int, default=0)
        parser.add_argument("--offset", type=int, default=0)
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--batch-size", type=int, default=50)
        parser.add_argument("--all-remaining", action="store_true")
        parser.add_argument("--resume-after", default="")
        parser.add_argument("--skip-existing", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")
        parser.add_argument("--strict-verification", action="store_true")
        parser.add_argument("--require-validated", action="store_true")
        parser.add_argument("--require-catalog-match", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--generate-assets", action="store_true")
        parser.add_argument(
            "--force-generate-assets",
            action="store_true",
            help="Generate assets even for review_required books (not just validated). Implies --generate-assets.",
        )
        parser.add_argument("--require-assets", action="store_true")
        parser.add_argument(
            "--perfect",
            action="store_true",
            help="Require validated extraction, catalog metadata match, strict persistence verification, and generated assets.",
        )
        parser.add_argument("--report-path", default="")
        parser.add_argument(
            "--last-chapter-title",
            default="",
            help="Expected title of the final chapter. When set, curation fails if this chapter is absent from the fetched TOC.",
        )

    def source_urls(self, options):
        explicit_urls = [normalize_source_url(url) for url in options["source_url"]]
        if explicit_urls:
            return explicit_urls

        queryset = SourceCatalogEntry.objects.order_by("source_url").values_list("source_url", flat=True)
        resume_after = (options["resume_after"] or "").strip()
        if resume_after:
            queryset = queryset.filter(source_url__gt=normalize_source_url(resume_after))
        offset = max(0, int(options["offset"] or 0))
        if options.get("all_remaining"):
            return list(queryset[offset:])
        limit = int(options["limit"] or 0) or int(options["batch_size"] or 50)
        return list(queryset[offset : offset + max(1, limit)])

    def write_report(self, summary, report_path):
        serializable_summary = {
            key: dict(value) if isinstance(value, Counter) else value
            for key, value in summary.items()
        }
        if report_path:
            report_path = Path(report_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(serializable_summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return serializable_summary

    def cleanup_iteration(self):
        # Local DEBUG query logging can retain large curated HTML/JSON INSERT payloads.
        reset_queries()
        for connection in connections.all():
            if connection.in_atomic_block:
                continue
            connection.close_if_unusable_or_obsolete()
        gc.collect()

    def disable_debug_query_logging(self):
        settings.DEBUG = False
        for connection in connections.all():
            connection.force_debug_cursor = False
        reset_queries()

    def handle(self, *args, **options):
        self.disable_debug_query_logging()
        if options["perfect"]:
            if options["skip_existing"]:
                raise CommandError("Perfect curation cannot use --skip-existing.")
            options["strict_verification"] = True
            options["require_validated"] = True
            options["require_catalog_match"] = True
            if not options["dry_run"]:
                options["generate_assets"] = True
                options["require_assets"] = True
        if options["force_generate_assets"]:
            options["generate_assets"] = True
        if options["require_assets"]:
            options["generate_assets"] = True

        if options["discover"]:
            max_pages = None if int(options["max_pages"] or 0) <= 0 else int(options["max_pages"])
            refreshed = TitleResolver().refresh_catalog(max_pages=max_pages)
            self.stdout.write(f"Discovered {len(refreshed)} new source catalog entries.")

        urls = self.source_urls(options)
        if not urls:
            raise CommandError("No source URLs found. Use --discover or pass --source-url.")
        normalized_urls = [normalize_source_url(url) for url in urls]
        catalog_entries = {
            normalize_source_url(entry.source_url): entry
            for entry in SourceCatalogEntry.objects.filter(source_url__in=[*urls, *normalized_urls])
        }

        summary = {
            "selected": len(urls),
            "processed": 0,
            "validated": 0,
            "review_required": 0,
            "invalid": 0,
            "failed": 0,
            "blocked": 0,
            "skipped_existing": 0,
            "verified": 0,
            "verification_failures": 0,
            "quarantined": 0,
            "quarantine_reasons": Counter(),
            "catalog_mismatches": 0,
            "dry_run": bool(options["dry_run"]),
            "assets_generated": 0,
            "asset_failures": 0,
            "entity_counts": Counter(),
            "structure_counts": Counter(),
            "validation_failures": Counter(),
            "review_required_reasons": Counter(),
            "last_source_url": "",
            "results": [],
        }
        report_path = options["report_path"]

        for source_url in urls:
            normalized_source_url = normalize_source_url(source_url)
            result = {
                "source_url": normalized_source_url,
                "title": "",
                "status": "",
                "structure_type": "",
                "validation_errors": [],
                "validation_warnings": [],
                "verification_errors": [],
                "catalog_errors": [],
                "skipped": False,
                "skip_reason": "",
                "blocked": False,
                "block_reason": "",
                "book_id": "",
                "curated_document_id": "",
                "error": "",
            }
            try:
                if options["skip_existing"] and CuratedBookDocument.objects.filter(source_url=normalized_source_url).exists():
                    summary["skipped_existing"] += 1
                    result["skipped"] = True
                    result["skip_reason"] = "curated_document_exists"
                    self.stdout.write(f"Skipping existing curated source {normalized_source_url}")
                    continue

                import hashlib
                from apps.processing.service_modules.scrape_cache import DiskPageCache, _get_scrape_cache_root
                url_hash = hashlib.md5(normalized_source_url.encode("utf-8")).hexdigest()
                page_cache = DiskPageCache(_get_scrape_cache_root() / f"curate_cmd_{url_hash}.jsonl")

                self.stdout.write(f"Curating {normalized_source_url}")
                content_limits = {}
                last_chapter_title = (options.get("last_chapter_title") or "").strip()
                if last_chapter_title:
                    content_limits["last_chapter_title"] = last_chapter_title
                curated = curate_book_document(normalized_source_url, content_limits=content_limits or None, page_cache=page_cache)
                document = curated["document"]
                validation = curated["validation"]
                status = str(document.get("status", ""))
                verification_errors = verify_curated_result(curated)
                catalog_errors = catalog_mismatch_errors(curated, catalog_entries.get(normalized_source_url))
                summary["processed"] += 1
                summary["last_source_url"] = normalized_source_url
                summary["entity_counts"].update(entity.get("entity_type", "") for entity in document.get("entities", []))
                summary["structure_counts"].update([document.get("structure_type", "")])
                summary["validation_failures"].update(validation.get("errors", []))
                result.update(
                    {
                        "title": document.get("book", {}).get("clean_title", ""),
                        "status": status,
                        "structure_type": document.get("structure_type", ""),
                        "validation_errors": validation.get("errors", []),
                        "validation_warnings": validation.get("warnings", []),
                        "verification_errors": verification_errors,
                        "catalog_errors": catalog_errors,
                    }
                )
                if status == "validated":
                    summary["validated"] += 1
                elif status == "invalid":
                    summary["invalid"] += 1
                    summary["review_required_reasons"].update(validation.get("errors", []))
                else:
                    summary["review_required"] += 1
                    summary["review_required_reasons"].update(validation.get("errors", []) or validation.get("warnings", []))

                if catalog_errors:
                    summary["catalog_mismatches"] += 1
                if options["require_validated"] and status != CuratedDocumentStatus.VALIDATED:
                    reasons = validation.get("errors", []) or validation.get("warnings", [])
                    detail = "; ".join(reasons) if reasons else status
                    raise CommandError(f"Curated document did not validate cleanly: {detail}")
                if catalog_errors and options["require_catalog_match"]:
                    raise CommandError("; ".join(catalog_errors))
                if verification_errors:
                    if options["strict_verification"]:
                        summary["verification_failures"] += 1
                        raise CommandError("; ".join(verification_errors))

                if options["dry_run"]:
                    if result["verification_errors"] or result["catalog_errors"]:
                        summary["verification_failures"] += 1
                    else:
                        summary["verified"] += 1
                    continue

                target_book = find_existing_book_by_source_url(normalized_source_url)
                if status == "invalid" and not curated["projection"].get("book_title"):
                    curated_document = persist_curated_document(curated)
                    result["curated_document_id"] = str(curated_document.id)
                    if result["verification_errors"]:
                        summary["verification_failures"] += 1
                    else:
                        summary["verified"] += 1
                    continue
                atomic_context = (
                    transaction.atomic()
                    if options["strict_verification"] or options["require_assets"]
                    else nullcontext()
                )
                persisted_book_id = ""
                persisted_document_id = ""
                persisted_verified = False
                with atomic_context:
                    book, _curated_document = persist_curated_book(
                        curated,
                        source_url=normalized_source_url,
                        target_book=target_book,
                    )
                    persisted_errors = verify_curated_result(
                        curated,
                        book=book,
                        curated_document=_curated_document,
                    )
                    result["verification_errors"].extend(
                        error for error in persisted_errors if error not in result["verification_errors"]
                    )
                    if result["verification_errors"]:
                        summary["verification_failures"] += 1
                        if options["strict_verification"]:
                            raise CommandError("; ".join(result["verification_errors"]))
                    else:
                        persisted_verified = True

                    generate_eligible = status == "validated" or (
                        options.get("force_generate_assets") and status == "review_required"
                    )
                    if options["generate_assets"] and generate_eligible:
                        try:
                            generate_exports(document)
                            sync_assets(book, None, curated["projection"])
                            summary["assets_generated"] += 1
                            page_cache.delete()
                        except Exception as exc:
                            summary["asset_failures"] += 1
                            book.state = LifecycleState.NEEDS_REVIEW
                            book.review_state = ReviewState.NEEDS_REVIEW
                            book.save(update_fields=["state", "review_state", "updated_at"])
                            self.stderr.write(f"Asset generation failed for {source_url}: {exc}")
                            if options["require_assets"]:
                                raise CommandError(f"Asset generation failed: {exc}")

                    gate_ok, gate_reasons = book_quality_gate(curated)
                    if not gate_ok:
                        book.state = LifecycleState.ARCHIVED
                        book.review_state = ReviewState.REJECTED
                        book.save(update_fields=["state", "review_state", "updated_at"])
                        summary["quarantined"] += 1
                        summary["quarantine_reasons"].update(gate_reasons)
                        result["quarantined"] = True
                        result["quarantine_reasons"] = gate_reasons
                        self.stderr.write(
                            f"Quarantined {normalized_source_url}: {','.join(gate_reasons)}"
                        )

                    persisted_book_id = str(book.id)
                    persisted_document_id = str(_curated_document.id)

                result["book_id"] = persisted_book_id
                result["curated_document_id"] = persisted_document_id
                if persisted_verified:
                    summary["verified"] += 1
            except Exception as exc:
                summary["failed"] += 1
                summary["blocked"] += 1
                result["blocked"] = True
                result["block_reason"] = "curation_gate_failed"
                result["error"] = str(exc)
                result["traceback"] = traceback.format_exc(limit=20)
                self.stderr.write(f"Curating failed for {normalized_source_url}: {exc}")
                if not options["continue_on_error"]:
                    raise
            finally:
                summary["results"].append(result)
                self.write_report(summary, report_path)
                self.cleanup_iteration()

        serializable_summary = self.write_report(summary, report_path)
        if report_path:
            self.stdout.write(f"Wrote report: {report_path}")
        self.stdout.write(json.dumps(serializable_summary, ensure_ascii=False, indent=2))
