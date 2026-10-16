from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.common.termination import termination_event
from apps.processing.automations.scheduler import run_automation_tick


class Command(BaseCommand):
    help = "Persist due source automation runs and dispatch records without broker I/O."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--interval", type=int, default=15)

    def handle(self, *args, **options):
        if not 1 <= options["interval"] <= 60:
            raise CommandError(
                "The schedule interval must be between 1 and 60 seconds."
            )
        with termination_event() as stopped:
            self.run_scheduler(stopped, options)

    def run_scheduler(self, stopped, options):
        while not stopped.is_set():
            close_old_connections()
            for run in run_automation_tick():
                self.stdout.write(
                    f"run_id={run.pk} state={run.state} code={run.error_code or '-'}"
                )
            if options["once"]:
                return
            stopped.wait(options["interval"])
