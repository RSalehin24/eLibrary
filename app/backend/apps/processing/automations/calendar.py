from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from apps.ingestion.services.curation_support.schedule import (
    day_interval_for_frequency,
    month_interval_for_frequency,
    shift_date_by_months,
)


def occurrence_at(automation, number):
    anchor = automation.first_run_at.astimezone(ZoneInfo(automation.time_zone))
    days = day_interval_for_frequency(automation.frequency)
    if days:
        local = anchor + timedelta(days=days * number)
    else:
        months = month_interval_for_frequency(automation.frequency)
        if months is None:
            raise ValueError("Unsupported automation frequency.")
        local = shift_date_by_months(anchor, months * number)
    # Round-trip a nonexistent wall time forward; an ambiguous time uses fold 0.
    return local.replace(fold=0).astimezone(UTC).astimezone(local.tzinfo)


def advance_automation(automation, now):
    number = automation.occurrence_number + 1
    while occurrence_at(automation, number) <= now:
        number += 1
    automation.next_run_at = occurrence_at(automation, number)
    missed = number - automation.occurrence_number - 1
    automation.occurrence_number = number
    automation.save(update_fields=["next_run_at", "occurrence_number", "updated_at"])
    return missed
