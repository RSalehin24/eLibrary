from uuid import UUID

from django.conf import settings
from django.db import connection
from django.db.models import F, Q
from django.utils import timezone

from apps.processing.job_models import JobDispatch

DISPATCHES_PER_WORKER = 2
SOURCE_DISPATCH_LOCK = 76002018


def work_lane(job):
    if job.error_code:
        return "recovery"
    return "continuation" if job.checkpoint.get("continuation") else "new"


def source_dispatch_candidates(eligible):
    # Dispatchers serialize admission, not execution, across the processing pool.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [SOURCE_DISPATCH_LOCK])
    outstanding = (
        JobDispatch.objects.filter(
            job__kind="process_source",
            generation=F("job__generation"),
            job__state__in=["queued", "retry_wait", "running"],
        )
        .filter(
            Q(state="published")
            | Q(state="leased", lease_expires_at__gt=timezone.now()),
        )
        .count()
    )
    available = max(
        0, DISPATCHES_PER_WORKER * settings.CELERY_PROCESSING_CONCURRENCY - outstanding
    )
    if not available:
        return []
    base = JobDispatch.objects.filter(
        eligible,
        job__kind="process_source",
        generation=F("job__generation"),
        job__state__in=["queued", "retry_wait"],
        available_at__lte=timezone.now(),
        job__available_at__lte=timezone.now(),
    )
    lanes = [
        Q(job__error_code="")
        & (
            Q(job__checkpoint__continuation__isnull=True)
            | Q(job__checkpoint__continuation=False)
        ),
        Q(job__error_code="", job__checkpoint__continuation=True),
        ~Q(job__error_code=""),
    ]
    previous = (
        JobDispatch.objects.filter(
            job__kind="process_source", published_at__isnull=False
        )
        .select_related("job")
        .order_by("-published_at")
        .first()
    )
    start = (
        {"new": 1, "continuation": 2, "recovery": 0}[work_lane(previous.job)]
        if previous
        else 0
    )
    selected: list[UUID] = []
    for offset in range(3 * available):
        candidate = (
            base.filter(lanes[(start + offset) % 3])
            .exclude(pk__in=selected)
            .order_by("job__available_at", "id")
            .first()
        )
        if candidate:
            selected.append(candidate.pk)
        if len(selected) == available:
            break
    return selected
