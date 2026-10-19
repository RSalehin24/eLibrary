from datetime import datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.processing.automation_models import SourceAutomation
from apps.processing.automations.services import create_automation

MAINTENANCE_ID = uuid5(NAMESPACE_URL, "library:unfinished-source-maintenance")


def next_maintenance_start():
    now = timezone.now().astimezone(ZoneInfo("Asia/Dhaka"))
    start = datetime.combine(now.date(), time(2), tzinfo=now.tzinfo)
    return start if start > now else start + timedelta(days=1)


class Command(BaseCommand):
    help = "Install the daily 2 AM Dhaka unfinished-book check without overriding existing schedules."

    def add_arguments(self, parser):
        parser.add_argument("--actor", type=int, required=True)

    def handle(self, *args, **options):
        actor = User.objects.filter(pk=options["actor"], is_active=True).first()
        if actor is None:
            raise CommandError("Choose an active processing manager.")
        existing = SourceAutomation.objects.filter(pk=MAINTENANCE_ID).first()
        existing = (
            existing
            or SourceAutomation.objects.filter(
                enabled=True, catalog_scope="unfinished", rebuild_updated=True
            ).first()
        )
        if existing is None:
            existing = create_automation(
                actor,
                {
                    "operation_id": MAINTENANCE_ID,
                    "name": "Unfinished book updates",
                    "enabled": True,
                    "frequency": "daily",
                    "time_zone": "Asia/Dhaka",
                    "first_run_local": next_maintenance_start().strftime(
                        "%Y-%m-%dT%H:%M"
                    ),
                    "catalog_scope": "unfinished",
                    "rebuild_updated": True,
                    "fetch_all": True,
                    "process_all": False,
                    "processing_limit": 0,
                },
            )
        self.stdout.write(
            f"Maintenance schedule: {existing.pk}; enabled={existing.enabled}."
        )
