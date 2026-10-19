import json
from uuid import UUID

from django.core.management.base import BaseCommand

from apps.ingestion.source_processing.audit import (
    audit_source_publication,
    published_source_operations,
)
from apps.ingestion.source_processing.quality_repair import queue_quality_repair
from apps.processing.jobs.execution_errors import ExecutionFailure


class Command(BaseCommand):
    help = "Audit available source evidence; --apply quarantines suspect books without deleting data."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--book", type=UUID, action="append", default=[])

    def handle(self, *args, **options):
        checked = 0
        operations = published_source_operations()
        if options["book"]:
            operations = operations.filter(book_id__in=options["book"])
        for job in operations.iterator(chunk_size=20):
            try:
                report = audit_source_publication(job, apply=options["apply"])
            except ExecutionFailure as error:
                from apps.catalog.content_quality import quarantine_book

                report = {
                    "operation_id": str(job.pk),
                    "book_id": str(job.book_id),
                    "verified": False,
                    "reason": error.failure.code,
                }
                if options["apply"]:
                    quarantine_book(job.book, report, actor=job.requested_by)
                    report.update(queue_quality_repair(job, report))
            self.stdout.write(json.dumps(report, ensure_ascii=False))
            checked += 1
        self.stderr.write(
            f"Checked {checked} sourced publications; apply={options['apply']}."
        )
