"""Automation schedule."""

from django.utils import timezone

from ..models import (
    ProcessingAutomationKind,
)
from . import automation_commands as _original
from . import catalog_progress_state as _progress
from . import service_imports_and_constants as _constants
from . import state_serializers as _state


def _local_scheduled_datetime(now, scheduled_time):
    local_now = timezone.localtime(now)
    return local_now.replace(
        hour=scheduled_time.hour,
        minute=scheduled_time.minute,
        second=0,
        microsecond=0,
    )


def automation_is_due(automation_settings, *, now=None):
    if not automation_settings.enabled:
        return False

    now = now or timezone.now()
    scheduled_at = _local_scheduled_datetime(now, automation_settings.time)
    local_now = timezone.localtime(now)
    if local_now < scheduled_at:
        return False

    last_run_at = automation_settings.last_run_at
    if last_run_at is None:
        return True

    last_local = timezone.localtime(last_run_at)
    days_since_last_run = (scheduled_at.date() - last_local.date()).days

    if automation_settings.interval == "daily":
        return last_local < scheduled_at
    if automation_settings.interval == "weekly":
        return days_since_last_run >= 7
    if automation_settings.interval == "biweekly":
        return days_since_last_run >= 14
    if automation_settings.interval == "monthly":
        return (
            scheduled_at.year,
            scheduled_at.month,
        ) != (
            last_local.year,
            last_local.month,
        )
    return days_since_last_run >= 7


def run_due_processing_automations(*, now=None):
    now = now or timezone.now()
    results = {}

    catalog_settings = _state.get_automation_settings(ProcessingAutomationKind.CATALOG)
    if automation_is_due(catalog_settings, now=now):
        state = _original.run_catalog_automation(
            trigger_source=_constants.SYNC_TRIGGER_SOURCE_SCHEDULER
        )
        results["catalog"] = {
            "ran": _progress.sync_run_mode(state)
            == _constants.SYNC_RUN_MODE_CATALOG_AUTOMATION,
            "status": state.status,
            "runMode": _progress.sync_run_mode(state),
        }
    else:
        results["catalog"] = {"ran": False, "status": "idle", "runMode": None}

    incomplete_settings = _state.get_automation_settings(
        ProcessingAutomationKind.INCOMPLETE
    )
    if automation_is_due(incomplete_settings, now=now):
        state = _original.run_incomplete_automation(
            trigger_source=_constants.SYNC_TRIGGER_SOURCE_SCHEDULER
        )
        results["incomplete"] = {
            "ran": _progress.sync_run_mode(state)
            == _constants.SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            "status": state.status,
            "runMode": _progress.sync_run_mode(state),
        }
    else:
        results["incomplete"] = {"ran": False, "status": "idle", "runMode": None}

    return results
