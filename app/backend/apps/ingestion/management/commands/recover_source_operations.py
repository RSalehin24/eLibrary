import json

from django.core.management.base import BaseCommand
from rest_framework.exceptions import APIException

from apps.ingestion.source_processing.policy import (
    MAX_SOURCE_CACHE_BYTES,
    MAX_SOURCE_PAGES,
)
from apps.ingestion.source_processing.recovery import restart_repaired_source
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure

RECOVERABLE_CODES = [
    "source_record_changed",
    "source_connection_unavailable",
    "worker_interrupted",
    "execution_interrupted",
    "source_content_unavailable",
    "source_checkpoint_limit",
]


class Command(BaseCommand):
    help = "Requeue recoverable unlinked source failures while preserving pages and attempt history."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        jobs = BackgroundJob.objects.filter(
            kind="process_source",
            state="failed",
            book__isnull=True,
            source_record__isnull=False,
            error_code__in=RECOVERABLE_CODES,
        ).select_related("requested_by")
        for job in jobs.iterator(chunk_size=20):
            if (
                job.checkpoint.get("cache_bytes", 0) >= MAX_SOURCE_CACHE_BYTES
                or job.checkpoint.get("pages_fetched", 0) >= MAX_SOURCE_PAGES
            ):
                continue
            report = {
                "operation_id": str(job.pk),
                "previous_error": job.error_code,
                "apply": options["apply"],
            }
            if options["apply"] and job.requested_by is None:
                report["recovery_error"] = "permission_revoked"
            elif options["apply"]:
                try:
                    repaired = restart_repaired_source(job.requested_by, job.pk)
                    report.update(
                        state=repaired.state,
                        pages_reused=repaired.checkpoint.get("pages_fetched", 0),
                    )
                except APIException as error:
                    report["recovery_error"] = error.default_code
                except ExecutionFailure as error:
                    report["recovery_error"] = error.failure.code
            self.stdout.write(json.dumps(report))
