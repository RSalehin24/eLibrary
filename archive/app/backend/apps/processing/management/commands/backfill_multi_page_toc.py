"""
Management command: backfill_multi_page_toc

Updates has_multi_page_toc / source_toc_page_count / fetched_toc_page_count on
BookCreationRequest rows that predate migration 0006 (or were processed before
the multi-page TOC detection code was deployed), using the multi-page fields
already stored in each book's latest CuratedBookDocument.source_snapshot.

Usage:
    python manage.py backfill_multi_page_toc
    python manage.py backfill_multi_page_toc --dry-run
    python manage.py backfill_multi_page_toc --batch-size 100
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ingestion.pipeline.curated_persistence import CuratedBookDocument
from apps.processing.models import BookCreationRequest


class Command(BaseCommand):
    help = "Backfill has_multi_page_toc fields from the latest CuratedBookDocument for each book."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be updated without writing to the database.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Number of requests to process per database batch (default: 200).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write("DRY RUN — no changes will be written.\n")

        # Only look at requests that have a linked book and have the default
        # value for has_multi_page_toc (meaning they were processed before the
        # detection code was deployed).
        requests_qs = (
            BookCreationRequest.objects.filter(
                has_multi_page_toc=False,
                linked_book__isnull=False,
            )
            .select_related("linked_book")
            .only("id", "linked_book_id", "has_multi_page_toc", "source_toc_page_count", "fetched_toc_page_count")
            .order_by("id")
        )

        total = requests_qs.count()
        self.stdout.write(f"Scanning {total} requests with has_multi_page_toc=False...\n")

        # Build a lookup of book_id → latest CuratedBookDocument source_structure
        # in batches to avoid loading everything into memory at once.
        updated = 0
        skipped_no_doc = 0
        skipped_no_data = 0
        skipped_single_page = 0

        offset = 0
        while offset < total:
            batch = list(requests_qs[offset : offset + batch_size])
            offset += batch_size

            book_ids = [r.linked_book_id for r in batch if r.linked_book_id]
            if not book_ids:
                continue

            # Fetch the latest CuratedBookDocument per book_id in one query.
            # We use a subquery approach: order by created_at DESC and take first.
            latest_docs = {}
            for doc in (
                CuratedBookDocument.objects.filter(book_id__in=book_ids)
                .order_by("book_id", "-created_at")
            ):
                if doc.book_id not in latest_docs:
                    latest_docs[doc.book_id] = doc

            to_update = []
            for r in batch:
                doc = latest_docs.get(r.linked_book_id)
                if doc is None:
                    skipped_no_doc += 1
                    continue

                ss = doc.source_snapshot or {}
                mf = ss.get("manifest") or {}
                struct = mf.get("source_structure") or {}

                has_paginated = struct.get("has_paginated_toc")
                if has_paginated is None:
                    # Old document pre-dating the new detection fields — skip.
                    skipped_no_data += 1
                    continue

                if not has_paginated:
                    skipped_single_page += 1
                    continue

                # Book is confirmed multi-page TOC.
                def _int(v, default=1):
                    try:
                        return max(int(v), default)
                    except (TypeError, ValueError):
                        return default

                src_pages = _int(struct.get("source_total_pages"), 1)
                fetched_pages = _int(struct.get("fetched_total_pages"), 1)
                pages_with_content = _int(struct.get("toc_pages_with_content"), 0)

                r.has_multi_page_toc = True
                r.source_toc_page_count = src_pages
                r.fetched_toc_page_count = max(pages_with_content, fetched_pages)
                to_update.append(r)

            if to_update:
                if dry_run:
                    for r in to_update:
                        self.stdout.write(
                            f"  WOULD UPDATE {r.pk}  src={r.source_toc_page_count}"
                            f"  fetched={r.fetched_toc_page_count}\n"
                        )
                else:
                    with transaction.atomic():
                        BookCreationRequest.objects.bulk_update(
                            to_update,
                            fields=["has_multi_page_toc", "source_toc_page_count", "fetched_toc_page_count", "updated_at"],
                        )
                updated += len(to_update)

            progress = min(offset, total)
            self.stdout.write(f"  {progress}/{total} processed, {updated} updated so far...\r", ending="")
            self.stdout.flush()

        self.stdout.write("\n")
        self.stdout.write(
            f"Done.\n"
            f"  Updated:              {updated}\n"
            f"  Skipped (no doc):     {skipped_no_doc}\n"
            f"  Skipped (old doc):    {skipped_no_data}\n"
            f"  Skipped (1 page):     {skipped_single_page}\n"
        )
