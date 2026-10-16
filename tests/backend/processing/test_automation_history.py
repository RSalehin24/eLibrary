from datetime import timedelta
from io import StringIO

import pytest
from apps.processing.automation_models import AutomationRun
from apps.processing.automations.scheduler import run_automation_tick
from automation_fixtures import NOW
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

pytestmark = pytest.mark.django_db


def test_history_uses_stable_pagination_and_constant_queries(automation, client):
    AutomationRun.objects.bulk_create(
        [
            AutomationRun(
                automation=automation,
                due_at=NOW + timedelta(days=number),
                state="blocked",
                error_code="discovery_already_active",
            )
            for number in range(30)
        ]
    )
    client.force_login(automation.run_as)
    path = f"/api/v1/manage/automations/{automation.pk}/runs/"
    with CaptureQueriesContext(connection) as small:
        first = client.get(f"{path}?limit=1")
    with CaptureQueriesContext(connection) as large:
        page = client.get(f"{path}?limit=24")
    assert first.status_code == page.status_code == 200
    assert len(small) == len(large) and len(large) <= 10
    assert page.json()["pagination"]["total_count"] == 30
    assert first.json()["entries"][0] == page.json()["entries"][0]
    assert all(row["processing_count"] == 0 for row in page.json()["entries"])


@pytest.mark.django_db(transaction=True)
def test_scheduler_command_runs_one_tick_without_a_broker(automation, monkeypatch):
    monkeypatch.setattr(
        "apps.processing.automations.scheduler.timezone.now", lambda: NOW
    )
    stream = StringIO()
    call_command("schedule_source_automations", once=True, stdout=stream)
    assert AutomationRun.objects.count() == 1 and "state=queued" in stream.getvalue()
    assert run_automation_tick(NOW) == []


@pytest.mark.parametrize("interval", [0, 61])
def test_scheduler_command_rejects_unbounded_intervals(interval):
    with pytest.raises(CommandError, match="between 1 and 60"):
        call_command("schedule_source_automations", once=True, interval=interval)
