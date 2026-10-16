from config.celery import app
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.common.termination import termination_event
from apps.processing.jobs.broker import AMQPPublisher
from apps.processing.jobs.dispatcher import dispatch_available
from apps.processing.jobs.maintenance import reconcile_background_jobs


class Command(BaseCommand):
    help = "Recover and dispatch persisted background jobs through confirmed AMQP publication."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run one bounded reconciliation/dispatch tick.",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=2,
            help="Seconds between ticks, from 1 to 60.",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        if not 1 <= interval <= 60:
            raise CommandError(
                "The dispatch interval must be between 1 and 60 seconds."
            )
        try:
            publisher = AMQPPublisher(app)
        except ValueError as error:
            raise CommandError(str(error)) from error
        with termination_event() as stopped:
            self.run_dispatcher(publisher, options, stopped)

    def run_dispatcher(self, publisher, options, stopped):
        while not stopped.is_set():
            close_old_connections()
            recovery = reconcile_background_jobs()
            outcome = dispatch_available(publisher)
            self.stdout.write(
                f"Recovered={recovery.recovered} reconciled={recovery.reconciled} republished={recovery.republished} confirmed={outcome.confirmed} pending={outcome.pending}"
            )
            if options["once"]:
                return
            stopped.wait(options["interval"])
