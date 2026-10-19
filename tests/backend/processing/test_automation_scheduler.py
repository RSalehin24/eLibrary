from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from apps.processing.automation_models import AutomationRun
from apps.processing.automations.calendar import occurrence_at
from apps.processing.automations.scheduler import run_automation_tick
from apps.processing.job_models import BackgroundJob, JobDispatch
from automation_fixtures import NOW

pytestmark = pytest.mark.django_db


def test_due_schedule_persists_one_occurrence_and_outbox(automation):
    runs = run_automation_tick(NOW)
    automation.refresh_from_db()
    assert len(runs) == 1 and runs[0].state == "queued"
    assert BackgroundJob.objects.count() == JobDispatch.objects.count() == 1
    assert automation.next_run_at == NOW + timedelta(days=1)
    assert run_automation_tick(NOW) == [] and AutomationRun.objects.count() == 1


def test_downtime_coalesces_occurrences_without_dispatch_storm(automation):
    runs = run_automation_tick(NOW + timedelta(days=8))
    automation.refresh_from_db()
    assert len(runs) == 1 and runs[0].missed_occurrences == 8
    assert automation.next_run_at == NOW + timedelta(days=9)
    assert BackgroundJob.objects.count() == 1


@pytest.mark.parametrize("change", ["disabled", "future"])
def test_ineligible_schedules_are_not_dispatched(automation, change):
    if change == "disabled":
        automation.enabled = False
    else:
        automation.next_run_at = NOW + timedelta(minutes=1)
    automation.save()
    assert run_automation_tick(NOW) == [] and not BackgroundJob.objects.exists()


def test_revoked_authority_is_recorded_without_a_job(automation):
    actor = automation.run_as
    actor.is_staff = False
    actor.save()
    run = run_automation_tick(NOW)[0]
    assert run.state == "blocked" and run.error_code == "permission_revoked"
    assert not BackgroundJob.objects.exists()


def test_busy_discovery_records_blocked_occurrence(automation):
    run_automation_tick(NOW)
    automation.next_run_at = NOW
    automation.occurrence_number = 0
    automation.pk = None
    automation.save()
    run = run_automation_tick(NOW)[0]
    assert run.error_code == "discovery_already_active" and run.state == "blocked"
    assert BackgroundJob.objects.count() == 1


def test_monthly_dates_retain_the_original_month_end_anchor(automation):
    automation.frequency = "monthly"
    automation.first_run_at = datetime(2027, 1, 31, 8, tzinfo=UTC)
    assert occurrence_at(automation, 1).day == 28
    assert occurrence_at(automation, 2).day == 31


def test_daylight_saving_gap_moves_forward_without_shifting_later_runs(automation):
    automation.time_zone = "America/New_York"
    automation.first_run_at = datetime(
        2027, 3, 13, 2, 30, tzinfo=ZoneInfo(automation.time_zone)
    )
    assert occurrence_at(automation, 1).hour == 3
    assert occurrence_at(automation, 2).hour == 2


@pytest.mark.parametrize(
    ("frequency", "days"), [("daily", 1), ("weekly", 7), ("biweekly", 14)]
)
def test_calendar_frequencies(automation, frequency, days):
    automation.frequency = frequency
    assert occurrence_at(automation, 1) == NOW + timedelta(days=days)


def test_unfinished_maintenance_keeps_scope_and_rebuild_policy_on_occurrence(
    automation,
):
    automation.catalog_scope = "unfinished"
    automation.rebuild_updated = True
    automation.save()
    run = run_automation_tick(NOW)[0]
    assert run.rebuild_updated
    assert run.job.input["command"]["catalog_scope"] == "unfinished"
    assert "/genres/" in run.job.input["command"]["catalog_url"]


def test_default_unfinished_maintenance_is_daily_dhaka_and_does_not_override_user_edits(
    automation,
):
    from apps.processing.automation_models import SourceAutomation
    from apps.processing.management.commands.ensure_source_maintenance import (
        MAINTENANCE_ID,
    )
    from django.core.management import call_command

    call_command("ensure_source_maintenance", actor=automation.run_as_id)
    maintenance = SourceAutomation.objects.get(pk=MAINTENANCE_ID)
    assert (
        maintenance.enabled
        and maintenance.rebuild_updated
        and maintenance.catalog_scope == "unfinished"
    )
    assert maintenance.frequency == "daily" and maintenance.time_zone == "Asia/Dhaka"
    assert maintenance.first_run_at.astimezone(ZoneInfo("Asia/Dhaka")).hour == 2
    assert maintenance.fetch_all and not maintenance.process_all
    maintenance.enabled = False
    maintenance.save()
    call_command("ensure_source_maintenance", actor=automation.run_as_id)
    maintenance.refresh_from_db()
    assert not maintenance.enabled
    assert SourceAutomation.objects.filter(pk=MAINTENANCE_ID).count() == 1
