import json
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.source_processing.defect_recovery import (
    defect_recovery_choice,
    recover_source_defect,
)
from apps.processing.job_models import BackgroundJob
from apps.processing.jobs.source_defects import SOURCE_DEFECT_CODES


class Command(BaseCommand):
    help = "Retry retained source defects only after relevant processing code changes."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--job", action="append", type=UUID, default=[])
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 1000:
            raise CommandError("Choose a limit from 1 to 1000.")
        jobs = BackgroundJob.objects.filter(
            kind="process_source",
            state__in=["failed", "needs_attention"],
            error_code__in=SOURCE_DEFECT_CODES,
            checkpoint__source_defect__fingerprint__isnull=False,
        ).select_related("requested_by", "source_record")
        if options["job"]:
            jobs = jobs.filter(pk__in=options["job"])
        for job in jobs.order_by("created_at", "id")[: options["limit"]]:
            outcome = "awaiting_code_or_input"
            if defect_recovery_choice(job):
                outcome = "would_retry"
                if options["apply"]:
                    outcome = "queued" if recover_source_defect(job.pk) else "changed"
            self.stdout.write(json.dumps({"job_id": str(job.pk), "outcome": outcome}))
