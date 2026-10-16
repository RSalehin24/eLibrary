from datetime import timedelta
from math import isfinite
from time import sleep

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ingestion.models import SourceRequestWindow
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def request_interval():
    try:
        interval = float(settings.SOURCE_REQUEST_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        interval = 0
    if not isfinite(interval) or not 0.25 <= interval <= 60:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_request_interval_invalid")
    return interval


@transaction.atomic
def reserve_source_slot(host):
    interval = request_interval()
    host = host.removeprefix("www.")
    SourceRequestWindow.objects.get_or_create(
        host=host, defaults={"available_at": timezone.now()}
    )
    window = SourceRequestWindow.objects.select_for_update().get(pk=host)
    now = timezone.now()
    delay = (window.available_at - now).total_seconds()
    if delay > 0:
        return delay
    window.available_at = now + timedelta(seconds=interval)
    window.save(update_fields=["available_at"])
    return 0


def wait_for_source_slot(host, boundary):
    delay = reserve_source_slot(host)
    while delay > 0:
        sleep(min(delay, 1))
        boundary()
        delay = reserve_source_slot(host)
