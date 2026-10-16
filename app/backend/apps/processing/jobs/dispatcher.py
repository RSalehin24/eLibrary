import logging
from dataclasses import dataclass

from apps.processing.jobs.broker import JobPublisher, PublishUnavailable
from apps.processing.jobs.dispatches import (
    claim_dispatches,
    record_dispatch_confirmation,
    record_dispatch_failure,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DispatchOutcome:
    confirmed: int
    pending: int


def dispatch_available(publisher: JobPublisher):
    confirmed = 0
    pending = 0
    for lease in claim_dispatches():
        try:
            publisher.publish(lease)
        except PublishUnavailable:
            record_dispatch_failure(lease)
            logger.warning(
                "Background job dispatch awaits retry.",
                extra={"dispatch_id": str(lease.identifier)},
            )
            pending += 1
        else:
            confirmed += int(record_dispatch_confirmation(lease))
    return DispatchOutcome(confirmed, pending)
