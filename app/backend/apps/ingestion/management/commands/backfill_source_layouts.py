import json
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.source_processing.layout_backfill import backfill_job_layout
from apps.processing.job_models import BackgroundJob


class Command(BaseCommand):
    help = "Backfill safe source layout diagnostics from exact retained job snapshots."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--job", action="append", type=UUID, default=[])
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 10000:
            raise CommandError("Choose a limit from 1 to 10000.")
        jobs = BackgroundJob.objects.filter(kind="process_source").exclude(
            state="running"
        )
        if options["job"]:
            jobs = jobs.filter(pk__in=options["job"])
        jobs = jobs.order_by("created_at", "id").only("kind", "state", "checkpoint")
        for job in jobs[: options["limit"]]:
            self.stdout.write(
                json.dumps(
                    {
                        "job_id": str(job.pk),
                        "outcome": backfill_job_layout(job, options["apply"]),
                    }
                )
            )
