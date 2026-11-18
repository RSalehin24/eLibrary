import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.common.source_site_batch_audit import (
    build_production_session,
    build_source_report,
    compare_source_report_to_production,
    ensure_report_dir,
    fetch_production_book_detail,
    fetch_production_book_index,
    iter_sharded_source_entries,
    refresh_source_archive,
    write_jsonl,
)


class Command(BaseCommand):
    help = (
        "Run a full-fidelity source site audit and optionally compare the "
        "results against production books through an authenticated read-only session."
    )

    def add_arguments(self, parser):
        parser.add_argument("--report-dir", default="tmp/source-site-audit")
        parser.add_argument("--refresh-archive", action="store_true")
        parser.add_argument(
            "--max-pages",
            type=int,
            default=0,
            help="When refreshing the source archive, stop after this many pages. Use 0 for exhaustion.",
        )
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--shard-count", type=int, default=1)
        parser.add_argument("--shard-index", type=int, default=0)
        parser.add_argument("--skip-production", action="store_true")
        parser.add_argument("--production-base-url", default="")
        parser.add_argument("--cookie-header", default="")

    def handle(self, *args, **options):
        shard_count = max(1, int(options["shard_count"] or 1))
        shard_index = max(0, int(options["shard_index"] or 0))
        if shard_index >= shard_count:
            raise CommandError("--shard-index must be smaller than --shard-count.")

        report_dir = ensure_report_dir(options["report_dir"])
        max_pages = None if int(options["max_pages"] or 0) <= 0 else int(options["max_pages"])
        limit = None if int(options["limit"] or 0) <= 0 else int(options["limit"])

        if options["refresh_archive"]:
            refresh_source_archive(max_pages=max_pages)

        production_index = {}
        production_session = None
        if not options["skip_production"]:
            base_url = (options["production_base_url"] or "").strip()
            cookie_header = (options["cookie_header"] or "").strip()
            if not base_url or not cookie_header:
                raise CommandError(
                    "Production comparison requires both --production-base-url and --cookie-header, or use --skip-production."
                )
            production_session = build_production_session(cookie_header=cookie_header)
            production_index = fetch_production_book_index(base_url, production_session)
        else:
            base_url = ""

        source_rows = []
        comparison_rows = []
        inspected = 0
        delta_count = 0

        for entry in iter_sharded_source_entries(
            shard_count=shard_count,
            shard_index=shard_index,
            limit=limit,
        ):
            inspected += 1
            self.stdout.write(f"[{inspected}] auditing {entry.source_url}")
            source_report = build_source_report(entry)
            source_rows.append(source_report)

            if production_session is None:
                continue

            production_summary = production_index.get(entry.source_url)
            production_detail = (
                fetch_production_book_detail(
                    base_url,
                    production_session,
                    production_summary["slug"],
                )
                if production_summary
                else None
            )
            comparison = compare_source_report_to_production(
                source_report,
                production_detail,
            )
            if comparison["has_deltas"]:
                delta_count += 1
            comparison_rows.append(comparison)

        source_path = Path(report_dir) / f"source-shard-{shard_index:03d}-of-{shard_count:03d}.jsonl"
        write_jsonl(source_path, source_rows)
        self.stdout.write(f"Wrote source report: {source_path}")

        if production_session is not None:
            comparison_path = (
                Path(report_dir)
                / f"comparison-shard-{shard_index:03d}-of-{shard_count:03d}.jsonl"
            )
            write_jsonl(comparison_path, comparison_rows)
            self.stdout.write(f"Wrote comparison report: {comparison_path}")

        summary_path = Path(report_dir) / f"summary-shard-{shard_index:03d}-of-{shard_count:03d}.json"
        summary_payload = {
            "inspected": inspected,
            "delta_count": delta_count,
            "shard_index": shard_index,
            "shard_count": shard_count,
            "production_compared": production_session is not None,
        }
        summary_path.write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.stdout.write(f"Wrote summary: {summary_path}")
