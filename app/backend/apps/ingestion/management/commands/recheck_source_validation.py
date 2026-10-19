import json

from django.core.management.base import BaseCommand
from rest_framework.exceptions import APIException

from apps.ingestion.source_processing.validation_recovery import (
    recover_source_validation,
    validation_recovery_evidence,
)
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.execution_errors import ExecutionFailure


class Command(BaseCommand):
    help = "Recheck held source validation with current rules; preserve chapters and attempt history."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        jobs = BackgroundJob.objects.filter(
            kind="process_source",
            book__isnull=True,
            state__in=["failed", "needs_attention"],
            error_code="source_content_incomplete",
        )
        for job in jobs.iterator(chunk_size=20):
            report = {"operation_id": str(job.pk), "apply": options["apply"]}
            try:
                evidence = validation_recovery_evidence(job)
                if evidence is None:
                    continue
                report["classification"] = evidence["classification"]
                if options["apply"]:
                    repaired = recover_source_validation(job.pk)
                    report["state"] = repaired.state if repaired else "unchanged"
            except APIException as error:
                report["recovery_error"] = error.default_code
            except ExecutionFailure as error:
                report["recovery_error"] = error.failure.code
            self.stdout.write(json.dumps(report))
