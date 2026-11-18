"""Management command to run the Central Job Engine.

Usage:
    python manage.py run_engine
"""

import logging

from django.core.management.base import BaseCommand

from apps.ingestion.engine.engine import JobEngine
from apps.ingestion.engine.redis_client import create_redis_client


class Command(BaseCommand):
    help = "Start the Central Job Engine"

    def add_arguments(self, parser):
        parser.add_argument(
            "--heartbeat-timeout",
            type=int,
            default=15,
            help="Seconds without heartbeat before worker is considered stale",
        )
        parser.add_argument(
            "--check-interval",
            type=int,
            default=2,
            help="Seconds between stale worker checks",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting Central Job Engine...")
        redis = create_redis_client()
        engine = JobEngine(
            redis,
            heartbeat_timeout=options["heartbeat_timeout"],
            heartbeat_check_interval=options["check_interval"],
        )

        self.stdout.write(self.style.SUCCESS("Engine started. Waiting for events..."))
        engine.start()

        try:
            import signal
            import sys

            def shutdown(signum, frame):
                self.stdout.write("Shutting down engine...")
                engine.stop()
                redis.close()
                sys.exit(0)

            signal.signal(signal.SIGINT, shutdown)
            signal.signal(signal.SIGTERM, shutdown)
            signal.pause()
        except KeyboardInterrupt:
            self.stdout.write("Stopping engine...")
            engine.stop()
            redis.close()
