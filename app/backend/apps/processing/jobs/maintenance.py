from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.ingestion.source_processing.defect_recovery import (
    recover_updated_source_defects,
)
from apps.ingestion.source_processing.validator_recovery import (
    recover_updated_source_validation,
)
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
        recover_stale_attempts(now - timedelta(seconds=STALE_HEARTBEAT_SECONDS))
        + recover_updated_source_defects()
        + recover_updated_source_validation(),
        reconcile_missing_dispatches(),
        republish_unstarted_jobs(now - timedelta(seconds=UNSTARTED_DISPATCH_SECONDS)),
    )
