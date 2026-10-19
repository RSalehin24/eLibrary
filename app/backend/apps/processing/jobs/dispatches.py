from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.processing.job_models import (
    BackgroundJobKind,
    BackgroundJobState,
    DispatchState,
    JobDispatch,
)

from .source_dispatch import source_dispatch_candidates

DISPATCH_LEASE_SECONDS = 30
MAX_DISPATCH_BATCH = 100
MAX_DISPATCH_BACKOFF_SECONDS = 60


@dataclass(frozen=True)
class DispatchLease:
    identifier: UUID
    owner: UUID
    queue: str


@transaction.atomic
def claim_dispatches(limit=50):
    if not 1 <= limit <= MAX_DISPATCH_BATCH:
        raise ValueError("Dispatch batch size must be between 1 and 100.")
    now = timezone.now()
    eligible = Q(state=DispatchState.PENDING) | Q(
        state=DispatchState.LEASED, lease_expires_at__lte=now
    )
    source_identifiers = source_dispatch_candidates(eligible)
    records = (
        JobDispatch.objects.select_for_update(skip_locked=True, of=("self",))
        .filter(
            eligible,
            available_at__lte=now,
            generation=F("job__generation"),
            job__state__in=[BackgroundJobState.QUEUED, BackgroundJobState.RETRY_WAIT],
            job__available_at__lte=now,
        )
        .filter(
            ~Q(job__kind=BackgroundJobKind.PROCESS_SOURCE)
            | Q(pk__in=source_identifiers)
        )
        .select_related("job")
        .order_by("available_at", "id")[:limit]
    )
    leases = []
    for dispatch in records:
        dispatch.owner = uuid4()
        dispatch.state = DispatchState.LEASED
        dispatch.lease_expires_at = now + timedelta(seconds=DISPATCH_LEASE_SECONDS)
        dispatch.save()
        queue = (
            "delivery"
            if dispatch.job.kind
            in {BackgroundJobKind.DELIVER_KINDLE, BackgroundJobKind.ACCOUNT_MAIL}
            else "processing"
        )
        leases.append(DispatchLease(dispatch.pk, dispatch.owner, queue))
    return leases


@transaction.atomic
def record_dispatch_confirmation(lease: DispatchLease):
    return (
        JobDispatch.objects.filter(
            pk=lease.identifier, owner=lease.owner, state=DispatchState.LEASED
        ).update(
            state=DispatchState.PUBLISHED,
            published_at=timezone.now(),
            lease_expires_at=None,
            owner=None,
            error_code="",
        )
        == 1
    )


@transaction.atomic
def record_dispatch_failure(lease: DispatchLease):
    dispatch = (
        JobDispatch.objects.select_for_update()
        .filter(pk=lease.identifier, owner=lease.owner, state=DispatchState.LEASED)
        .first()
    )
    if dispatch is None:
        return False
    dispatch.failure_count += 1
    delay = min(2 ** min(dispatch.failure_count, 6), MAX_DISPATCH_BACKOFF_SECONDS)
    dispatch.available_at = timezone.now() + timedelta(seconds=delay)
    dispatch.state = DispatchState.PENDING
    dispatch.error_code = "broker_publish_failed"
    dispatch.owner = None
    dispatch.lease_expires_at = None
    dispatch.save()
    return True
