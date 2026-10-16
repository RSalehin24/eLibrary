from datetime import UTC, datetime

from apps.accounts.models import User
from apps.processing.automation_models import SourceAutomation

NOW = datetime(2026, 10, 15, 8, tzinfo=UTC)


def create_automation(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_CATALOG_URL = "https://source.test/books/"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    actor = User.objects.create_user(email="schedule@library.test", is_staff=True)
    return SourceAutomation.objects.create(
        name="দৈনিক সংগ্রহ",
        enabled=True,
        frequency="daily",
        first_run_at=NOW,
        next_run_at=NOW,
        time_zone="Asia/Dhaka",
        run_as=actor,
    )
