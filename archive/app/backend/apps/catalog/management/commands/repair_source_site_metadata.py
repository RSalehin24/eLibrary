import gc
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import (
    Book,
    BookContributor,
    BookSource,
    Contributor,
    ContributorRole,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.catalog.services import replace_book_relations
from apps.common.models import LifecycleState
from apps.common.text import (
    clean_display_text,
    clean_entity_display_text,
    normalize_catalog_text,
)
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.pipeline import epub_book
from apps.ingestion.services.normalization import normalize_scraped_book
from apps.ingestion.services.normalization_support.metadata import (
    has_non_name_phrase_marker,
    looks_like_contributor_name,
)
from apps.ingestion.services.resolution_support_metadata import split_display_title
from apps.ingestion.services.submissions_support.assets import calculate_checksum
from apps.processing.models import BookCreationRequest, BookCreationRequestState, BookRecord
from apps.processing.services import kickoff_request_processing


NAV_ITEMREF_PATTERN = re.compile(
    r"(?P<line>\n?[ \t]*<itemref\b(?=[^>]*\bidref=[\"']nav[\"'])(?P<attrs>[^>]*)/>\s*)",
    re.IGNORECASE,
)
FIRST_ITEMREF_PATTERN = re.compile(r"<itemref\b[^>]*/>", re.IGNORECASE)


def parsed_source_title_and_author(entry):
    raw_data = entry.raw_data if isinstance(entry.raw_data, dict) else {}
    display_title = raw_data.get("full_title") or raw_data.get("display_title") or entry.title
    title, title_author = split_display_title(display_title)
    author_line = raw_data.get("meta_author_line") or title_author
    return title or entry.title, author_line or ""


def relation_names(book, role):
    return [
        relation.contributor.name
        for relation in book.book_contributors.select_related("contributor")
        if relation.role == role
    ]


def collect_garbage(index, interval=25):
    if index % interval == 0:
        gc.collect()


def update_source_entries(dry_run=False, limit=0):
    changed = 0
    queryset = SourceCatalogEntry.objects.order_by("id")
    if limit:
        queryset = queryset[:limit]
    for index, entry in enumerate(queryset.iterator(chunk_size=25), start=1):
        title, author_line = parsed_source_title_and_author(entry)
        raw_data = entry.raw_data if isinstance(entry.raw_data, dict) else {}
        next_raw_data = {
            **raw_data,
            "title": title,
            "author_line": author_line,
            "title_author_line": author_line if not raw_data.get("meta_author_line") else raw_data.get("title_author_line", ""),
        }
        updates = {}
        if entry.title != title:
            updates["title"] = title
            updates["normalized_title"] = normalize_catalog_text(title)
        if entry.author_line != author_line:
            updates["author_line"] = author_line
        if raw_data != next_raw_data:
            updates["raw_data"] = next_raw_data
        if updates:
            changed += 1
            if not dry_run:
                for field, value in updates.items():
                    setattr(entry, field, value)
                entry.save(update_fields=[*updates, "updated_at"])
        collect_garbage(index)
    return changed


def preferred_source_title(book):
    source = book.source_urls.select_related(None).first()
    if not source:
        return ""
    source_entry = SourceCatalogEntry.objects.filter(source_url=source.normalized_source_url).first()
    if not source_entry:
        return ""
    return parsed_source_title_and_author(source_entry)[0]


def update_books(dry_run=False, limit=0):
    changed = 0
    queryset = Book.objects.filter(raw_scrape_payload__isnull=False).order_by("id")
    if limit:
        queryset = queryset[:limit]
    for index, book in enumerate(queryset.iterator(chunk_size=10), start=1):
        payload = book.raw_scrape_payload if isinstance(book.raw_scrape_payload, dict) else {}
        if not payload:
            continue
        title = preferred_source_title(book) or payload.get("book_title") or book.title
        payload = {**payload, "book_title": title}
        normalized = normalize_scraped_book(payload)
        updates = {
            "title": title,
            "raw_scrape_payload": payload,
            "raw_scraped_metadata": {
                **normalized.get("raw_strings", {}),
                "source_url": next(iter(book.source_urls.values_list("normalized_source_url", flat=True)), ""),
            },
        }
        changed += 1
        if dry_run:
            continue
        for field, value in updates.items():
            setattr(book, field, value)
        book.save(update_fields=[*updates, "updated_at"])
        replace_book_relations(
            book,
            contributors=normalized["contributors"],
            series_names=normalized["series"],
            category_names=normalized["categories"],
        )
        BookSource.objects.filter(book=book).update(source_title=book.title)
        collect_garbage(index, interval=10)
    return changed


def update_processing_records(dry_run=False, limit=0):
    changed = 0
    queryset = BookRecord.objects.select_related("linked_book", "source_catalog_entry").order_by("id")
    if limit:
        queryset = queryset[:limit]
    for index, record in enumerate(queryset.iterator(chunk_size=50), start=1):
        updates = {}
        if record.linked_book_id:
            book = record.linked_book
            updates = {
                "name": book.title,
                "writer": ", ".join(relation_names(book, ContributorRole.AUTHOR)),
                "translator": ", ".join(relation_names(book, ContributorRole.TRANSLATOR)),
                "publisher": ", ".join(relation_names(book, ContributorRole.PUBLISHER)),
            }
        elif record.source_catalog_entry_id:
            title, author_line = parsed_source_title_and_author(record.source_catalog_entry)
            raw_data = record.source_catalog_entry.raw_data
            raw_data = raw_data if isinstance(raw_data, dict) else {}
            updates = {
                "name": title,
                "writer": author_line,
                "category": raw_data.get("category") or record.category,
            }
        updates = {key: value for key, value in updates.items() if getattr(record, key) != value}
        if updates:
            changed += 1
            if not dry_run:
                for field, value in updates.items():
                    setattr(record, field, value)
                record.save(update_fields=[*updates, "updated_at"])
        collect_garbage(index, interval=50)
    return changed


def clean_contributor_display_names(dry_run=False):
    changed = 0
    for contributor in Contributor.objects.iterator(chunk_size=100):
        cleaned = clean_entity_display_text(contributor.name)
        if cleaned and cleaned != contributor.name:
            changed += 1
            if not dry_run:
                contributor.name = cleaned
                contributor.save(update_fields=["name", "normalized_name", "slug", "catalog_code", "updated_at"])
    return changed


def contributor_name_is_noise(value):
    cleaned = clean_entity_display_text(value)
    if not cleaned:
        return True
    if has_non_name_phrase_marker(cleaned):
        return True
    if any(looks_like_contributor_name(cleaned, role=role) for role in (
        ContributorRole.AUTHOR,
        ContributorRole.TRANSLATOR,
        ContributorRole.EDITOR,
        ContributorRole.PUBLISHER,
        ContributorRole.COVER_ARTIST,
        ContributorRole.ILLUSTRATOR,
    )):
        return False
    return True


def delete_invalid_book_contributions(dry_run=False):
    """Remove BookContributor rows whose contributor name fails the
    role-specific ``looks_like_contributor_name`` check (e.g. title
    fragments like ``"\u09e8 \u099b\u09cb\u099f\u0997\u09b2\u09cd\u09aa"`` or full-sentence
    translator rows). The contributor records themselves are kept;
    :func:`delete_invalid_orphan_contributors` will sweep up any that
    become unreferenced.
    """
    deleted = 0
    queryset = BookContributor.objects.select_related("contributor").order_by("id")
    for index, relation in enumerate(queryset.iterator(chunk_size=100), start=1):
        name = relation.contributor.name if relation.contributor_id else ""
        if not name:
            continue
        if looks_like_contributor_name(name, role=relation.role):
            continue
        deleted += 1
        if not dry_run:
            relation.delete()
        collect_garbage(index, interval=100)
    return deleted


def delete_invalid_orphan_contributors(dry_run=False):
    deleted = 0
    queryset = Contributor.objects.filter(
        book_contributions__isnull=True,
        permission_grants__isnull=True,
    ).distinct()
    for contributor in queryset.iterator(chunk_size=100):
        if not contributor_name_is_noise(contributor.name):
            continue
        deleted += 1
        if not dry_run:
            contributor.delete()
    return deleted


def epub_path_for_asset(asset):
    if asset.file and asset.file.name:
        try:
            path = Path(asset.file.path)
            if path.exists():
                return path
        except (AttributeError, NotImplementedError, TypeError, ValueError):
            pass
    if asset.legacy_path:
        path = Path(asset.legacy_path)
        if path.exists():
            return path
    return None


def nav_itemref_is_first(opf_text):
    spine_match = re.search(r"<spine\b[^>]*>(?P<body>.*?)</spine>", opf_text, re.IGNORECASE | re.DOTALL)
    if not spine_match:
        return False
    first_itemref = FIRST_ITEMREF_PATTERN.search(spine_match.group("body"))
    return bool(first_itemref and re.search(r"\bidref=[\"']nav[\"']", first_itemref.group(0), re.IGNORECASE))


def repaired_opf_nav_spine(opf_text):
    spine_match = re.search(r"(?P<open><spine\b[^>]*>)(?P<body>.*?)(?P<close></spine>)", opf_text, re.IGNORECASE | re.DOTALL)
    if not spine_match:
        return opf_text, False

    body = spine_match.group("body")
    nav_matches = list(NAV_ITEMREF_PATTERN.finditer(body))
    if not nav_matches:
        return opf_text, False

    nav_first = nav_itemref_is_first(opf_text)
    nav_linear_missing = any("linear=" not in match.group("attrs").lower() for match in nav_matches)
    if not nav_first and not nav_linear_missing:
        return opf_text, False

    body_without_nav = NAV_ITEMREF_PATTERN.sub("\n", body).rstrip()
    indent_match = re.search(r"\n(?P<indent>[ \t]*)<itemref\b", body_without_nav)
    indent = indent_match.group("indent") if indent_match else "    "
    repaired_body = f"{body_without_nav}\n{indent}<itemref idref=\"nav\" linear=\"no\"/>\n  "
    repaired_spine = f"{spine_match.group('open')}{repaired_body}{spine_match.group('close')}"
    return (
        opf_text[: spine_match.start()]
        + repaired_spine
        + opf_text[spine_match.end() :],
        True,
    )


def repair_epub_nav_spine_file(epub_path, dry_run=False):
    epub_path = Path(epub_path)
    if not epub_path.exists():
        return False

    try:
        with zipfile.ZipFile(epub_path, "r") as archive:
            names = archive.namelist()
            opf_name = next((name for name in names if name.endswith("content.opf")), "")
            if not opf_name:
                return False
            opf_text = archive.read(opf_name).decode("utf-8")
            repaired_opf, changed = repaired_opf_nav_spine(opf_text)
            if not changed:
                return False
            if dry_run:
                return True

            with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as temp_file:
                temp_path = Path(temp_file.name)

            try:
                with zipfile.ZipFile(temp_path, "w") as output:
                    for item in archive.infolist():
                        data = (
                            repaired_opf.encode("utf-8")
                            if item.filename == opf_name
                            else archive.read(item.filename)
                        )
                        output.writestr(item, data)
                shutil.move(str(temp_path), epub_path)
            finally:
                if temp_path.exists():
                    temp_path.unlink()
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile):
        return False
    return True


def repair_existing_epub_nav_spines(dry_run=False, limit=0):
    repaired = 0
    queryset = GeneratedAsset.objects.filter(
        asset_type=GeneratedAssetType.EPUB,
        status=GeneratedAssetStatus.READY,
    ).order_by("id")
    if limit:
        queryset = queryset[:limit]

    for asset in queryset.iterator(chunk_size=25):
        path = epub_path_for_asset(asset)
        if not path or not repair_epub_nav_spine_file(path, dry_run=dry_run):
            continue
        repaired += 1
        if not dry_run:
            asset.file_size = path.stat().st_size
            asset.checksum = calculate_checksum(path)
            asset.save(update_fields=["file_size", "checksum", "updated_at"])
    return repaired


def epub_content_opf_is_readable(path):
    try:
        with zipfile.ZipFile(path, "r") as archive:
            opf_name = next(
                (name for name in archive.namelist() if name.endswith("content.opf")),
                "",
            )
            if not opf_name:
                return False
            archive.read(opf_name)
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile):
        return False
    return True


def copy_cover_for_epub_regeneration(book, payload, output_folder):
    cover_asset = book.generated_assets.filter(
        asset_type=GeneratedAssetType.COVER,
        status=GeneratedAssetStatus.READY,
    ).first()
    cover_path = epub_path_for_asset(cover_asset) if cover_asset else None
    if not cover_path:
        return payload.get("cover", "")

    cover_name = payload.get("cover") or cover_path.name
    destination = output_folder / Path(str(cover_name)).name
    shutil.copy2(cover_path, destination)
    return destination.name


def epub_regeneration_payload(book, output_folder):
    payload = book.raw_scrape_payload if isinstance(book.raw_scrape_payload, dict) else {}
    payload = {
        **payload,
        "book_title": book.title,
        "main_content": payload.get("main_content") or book.main_content_html,
        "book_info": payload.get("book_info") or book.book_info_html,
        "dedication": payload.get("dedication") or book.dedication_html,
        "toc": payload.get("toc") or book.toc,
        "content_items": payload.get("content_items") or book.content_items,
        "front_sections": payload.get("front_sections") or [],
        "back_sections": payload.get("back_sections") or [],
        "output_folder": str(output_folder),
    }
    payload["cover"] = copy_cover_for_epub_regeneration(book, payload, output_folder)
    return payload


def regenerate_corrupt_epub_assets(dry_run=False, limit=0):
    regenerated = 0
    queryset = (
        GeneratedAsset.objects.filter(
            asset_type=GeneratedAssetType.EPUB,
            status=GeneratedAssetStatus.READY,
        )
        .select_related("book")
        .order_by("id")
    )
    if limit:
        queryset = queryset[:limit]

    for asset in queryset.iterator(chunk_size=25):
        path = epub_path_for_asset(asset)
        if path and epub_content_opf_is_readable(path):
            continue
        book = asset.book
        if not isinstance(book.raw_scrape_payload, dict) or not book.raw_scrape_payload:
            continue
        regenerated += 1
        if dry_run:
            continue
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            payload = epub_regeneration_payload(book, output_folder)
            epub_book.create_epub(payload)
            epub_candidates = sorted(output_folder.glob("*.epub"))
            if not epub_candidates:
                continue
            generated_path = epub_candidates[0]
            if asset.file and asset.file.name:
                asset.file.delete(save=False)
            with open(generated_path, "rb") as handle:
                asset.file.save(generated_path.name, File(handle), save=False)
            asset.status = GeneratedAssetStatus.READY
            asset.storage_path = asset.file.name
            asset.legacy_path = ""
            asset.content_type = "application/epub+zip"
            asset.file_size = asset.file.size
            asset.checksum = calculate_checksum(asset.file.path)
            asset.save(
                update_fields=[
                    "status",
                    "storage_path",
                    "legacy_path",
                    "content_type",
                    "file_size",
                    "checksum",
                    "updated_at",
                ]
            )
    return regenerated


def soft_delete_duplicate_failed_books(dry_run=False):
    changed = 0
    source_book_ids = set(BookSource.objects.values_list("book_id", flat=True))
    for title in (
        Book.objects.filter(state=LifecycleState.NEEDS_REVIEW, source_urls__isnull=True, deleted_at__isnull=True)
        .order_by("title")
        .values_list("title", flat=True)
        .distinct()
    ):
        books = Book.objects.filter(title=title, source_urls__isnull=True, state=LifecycleState.NEEDS_REVIEW, deleted_at__isnull=True)
        if not Book.objects.filter(title=title, id__in=source_book_ids).exists():
            continue
        for book in books:
            changed += 1
            if not dry_run:
                book.state = LifecycleState.SOFT_DELETED
                book.deleted_at = timezone.now()
                book.save(update_fields=["state", "deleted_at", "updated_at"])
    return changed


def retry_failed_epub_requests(dry_run=False):
    retried = 0
    requests = BookCreationRequest.objects.filter(
        state=BookCreationRequestState.FAILED,
        error_message__icontains="Missing generated assets: EPUB",
    )
    for request in requests:
        retried += 1
        if dry_run:
            continue
        request.state = BookCreationRequestState.QUEUED
        request.error_message = ""
        request.save(update_fields=["state", "error_message", "updated_at"])
        kickoff_request_processing(request.id)
    return retried


class Command(BaseCommand):
    help = "Repair source-site-derived metadata, processing rows, duplicate failed books, and failed EPUB requests."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--retry-failed-epubs", action="store_true")
        parser.add_argument("--repair-epub-nav", action="store_true")
        parser.add_argument("--regenerate-corrupt-epubs", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = max(0, int(options["limit"] or 0))
        source_entries_changed = update_source_entries(dry_run=dry_run, limit=limit)
        books_renormalized = update_books(dry_run=dry_run, limit=limit)
        contributors_renamed = clean_contributor_display_names(dry_run=dry_run)
        processing_records_changed = update_processing_records(dry_run=dry_run, limit=limit)
        invalid_book_contributions_deleted = delete_invalid_book_contributions(dry_run=dry_run)
        invalid_orphan_contributors_deleted = delete_invalid_orphan_contributors(dry_run=dry_run)
        epub_nav_spines_repaired = (
            repair_existing_epub_nav_spines(dry_run=dry_run, limit=limit)
            if options["repair_epub_nav"]
            else 0
        )
        corrupt_epubs_regenerated = (
            regenerate_corrupt_epub_assets(dry_run=dry_run, limit=limit)
            if options["regenerate_corrupt_epubs"]
            else 0
        )
        retried = retry_failed_epub_requests(dry_run=dry_run) if options["retry_failed_epubs"] else 0
        summary = {
            "source_entries_changed": source_entries_changed,
            "books_renormalized": books_renormalized,
            "contributors_renamed": contributors_renamed,
            "invalid_book_contributions_deleted": invalid_book_contributions_deleted,
            "invalid_orphan_contributors_deleted": invalid_orphan_contributors_deleted,
            "processing_records_changed": processing_records_changed,
            "epub_nav_spines_repaired": epub_nav_spines_repaired,
            "corrupt_epubs_regenerated": corrupt_epubs_regenerated,
            "duplicate_failed_books_deleted": soft_delete_duplicate_failed_books(dry_run=dry_run),
            "failed_epub_requests_retried": retried,
        }
        self.stdout.write(str(summary))
