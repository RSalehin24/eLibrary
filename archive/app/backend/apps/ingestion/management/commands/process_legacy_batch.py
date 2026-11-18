from django.core.management.base import BaseCommand

from apps.ingestion.models import JobType, ProcessingJob
from apps.ingestion.services.submissions import (
    create_submission_records,
    legacy_config_entries_as_submission_inputs,
    process_submission_job,
    queue_submission,
)


class Command(BaseCommand):
    help = "Wrap the legacy batch scraper behind the Django ingestion pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--url", action="append", dest="urls", default=[])
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run the queued jobs synchronously in-process instead of through Celery.",
        )

    def handle(self, *args, **options):
        entries = [{"kind": "url", "value": value} for value in options["urls"]]
        if not entries:
            entries = legacy_config_entries_as_submission_inputs()

        if not entries:
            self.stderr.write("No URLs supplied and no legacy config entries were found.")
            return

        submissions = create_submission_records(None, entries, auto_process=False)
        for submission in submissions:
            if not submission.resolved_url:
                self.stdout.write(f"Skipped unresolved submission: {submission.original_input}")
                continue
            if options["sync"]:
                job = ProcessingJob.objects.create(submission=submission, job_type=JobType.INGESTION)
                process_submission_job(str(job.id))
                self.stdout.write(f"Processed job {job.id} synchronously.")
                continue

            job = queue_submission(submission)
            self.stdout.write(f"Queued {submission.original_input} as job {job.id}")
