from datetime import timedelta
from email.utils import parsedate_to_datetime

from django.db import transaction
from django.utils import timezone

from apps.ingestion.models import SourceHostHealth
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

CIRCUIT_INTERVAL = timedelta(minutes=5)


def retry_after(value):
    if not value:
        return None
    try:
        parsed = timezone.now() + timedelta(seconds=max(0, int(value)))
    except (ValueError, OverflowError):
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if timezone.is_naive(parsed):
        return None
    return parsed if parsed > timezone.now() else None


@transaction.atomic
def require_healthy_host(host):
    host = host.removeprefix("www.")
    now = timezone.now()
    health, _ = SourceHostHealth.objects.select_for_update().get_or_create(host=host)
    if health.open_until and health.open_until > now:
        raise ExecutionFailure(FailureKind.TRANSIENT, "source_circuit_open")
    if health.failure_count >= 5:
        health.open_until = now + CIRCUIT_INTERVAL
        health.save(update_fields=["open_until"])


@transaction.atomic
def record_host_response(host, status):
    host = host.removeprefix("www.")
    health, _ = SourceHostHealth.objects.select_for_update().get_or_create(host=host)
    now = timezone.now()
    if status < 400:
        health.failure_count, health.window_started_at, health.open_until = (
            0,
            None,
            None,
        )
    elif status in {408, 429} or status >= 500:
        if (
            not health.window_started_at
            or now - health.window_started_at >= CIRCUIT_INTERVAL
        ):
            health.failure_count, health.window_started_at = 0, now
        health.failure_count += 1
        if health.failure_count >= 5:
            health.open_until = now + CIRCUIT_INTERVAL
    health.save()
