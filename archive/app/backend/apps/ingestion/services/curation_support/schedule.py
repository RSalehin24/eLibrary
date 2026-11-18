from calendar import monthrange
from datetime import datetime, timedelta

from django.utils import timezone

from apps.ingestion.models import CatalogAutomationFrequency


def normalize_refresh_max_pages(value):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return None


def combine_local_date_and_time(date_value, time_value):
    return timezone.make_aware(
        datetime.combine(date_value, time_value),
        timezone.get_current_timezone(),
    )


def day_interval_for_frequency(frequency):
    intervals = {
        CatalogAutomationFrequency.DAILY: 1,
        CatalogAutomationFrequency.WEEKLY: 7,
        CatalogAutomationFrequency.BIWEEKLY: 14,
    }
    return intervals.get(frequency)


def month_interval_for_frequency(frequency):
    intervals = {
        CatalogAutomationFrequency.MONTHLY: 1,
        CatalogAutomationFrequency.BIMONTHLY: 2,
        CatalogAutomationFrequency.QUARTERLY: 3,
        CatalogAutomationFrequency.FOUR_MONTHLY: 4,
        CatalogAutomationFrequency.HALF_YEARLY: 6,
    }
    return intervals.get(frequency)


def shift_date_by_months(date_value, months):
    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date_value.day, monthrange(year, month)[1])
    return date_value.replace(year=year, month=month, day=day)


def next_catalog_automation_due_at(settings_obj, now=None, latest_run=None):
    now = timezone.localtime(now or timezone.now())
    today_slot = combine_local_date_and_time(now.date(), settings_obj.daily_run_time)
    latest_run_at = timezone.localtime(latest_run.created_at) if latest_run else None
    settings_updated_at = timezone.localtime(settings_obj.updated_at or settings_obj.created_at)

    if latest_run_at is None or settings_updated_at > latest_run_at:
        return today_slot

    day_interval = day_interval_for_frequency(settings_obj.frequency)
    if day_interval:
        next_date = latest_run_at.date() + timedelta(days=day_interval)
        return combine_local_date_and_time(next_date, settings_obj.daily_run_time)

    month_interval = month_interval_for_frequency(settings_obj.frequency)
    if month_interval:
        next_date = shift_date_by_months(latest_run_at.date(), month_interval)
        return combine_local_date_and_time(next_date, settings_obj.daily_run_time)

    return today_slot

