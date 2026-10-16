from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.processing.jobs.recovery import (
    reconcile_missing_dispatches,
    recover_stale_attempts,
    republish_unstarted_jobs,
)

STALE_HEARTBEAT_SECONDS = 180
UNSTARTED_DISPATCH_SECONDS = 60


@dataclass(frozen=True)
class RecoveryOutcome:
    recovered: int
    reconciled: int
    republished: int


def reconcile_background_jobs():
    now = timezone.now()
    return RecoveryOutcome(
        recover_stale_attempts(now - timedelta(seconds=STALE_HEARTBEAT_SECONDS)),
        reconcile_missing_dispatches(),
        republish_unstarted_jobs(now - timedelta(seconds=UNSTARTED_DISPATCH_SECONDS)),
    )
