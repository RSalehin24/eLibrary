from django.core.management.base import BaseCommand
from django.db.models import F

from apps.processing.job_models import JobDispatch
from apps.processing.jobs.source_admission import fence_source_dispatch


class Command(BaseCommand):
    help = "Fence already-published source messages so bounded admission can resume; preserves broker and database history."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        identifiers = list(
            JobDispatch.objects.filter(
                state="published",
                job__kind="process_source",
                generation=F("job__generation"),
                job__state__in=["queued", "retry_wait"],
            ).values_list("job_id", flat=True)
        )
        count = (
            sum(fence_source_dispatch(identifier) for identifier in identifiers)
            if options["apply"]
            else len(identifiers)
        )
        self.stdout.write(f"Source dispatches: {count}; apply={options['apply']}.")
