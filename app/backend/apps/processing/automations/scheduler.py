from uuid import uuid5

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.ingestion.source_discovery.commands import request_source_discovery
from apps.ingestion.source_discovery.configuration import discovery_configuration
from apps.processing.automation_models import AutomationRun, SourceAutomation
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .calendar import advance_automation

SCHEDULER_BATCH_SIZE = 20


def occurrence_job(automation, due_at):
    require_processing_manager(automation.run_as)
    configured = discovery_configuration()
    return request_source_discovery(
        automation.run_as,
        {
            "operation_id": uuid5(automation.pk, due_at.isoformat()),
            "configuration_revision": configured["configuration_revision"],
            "max_pages": automation.source_max_pages,
        },
    )


def enqueue_occurrence(automation, due_at, missed):
    values = {
        "automation": automation,
        "due_at": due_at,
        "processing_limit": automation.processing_limit,
        "missed_occurrences": missed,
    }
    try:
        job = occurrence_job(automation, due_at)
    except PermissionDenied:
        return AutomationRun.objects.create(
            **values, state="blocked", error_code="permission_revoked"
        )
    except ExecutionFailure as error:
        return AutomationRun.objects.create(
            **values, state="blocked", error_code=error.failure.code
        )
    except JobStateConflict:
        return AutomationRun.objects.create(
            **values, state="blocked", error_code="discovery_already_active"
        )
    return AutomationRun.objects.create(**values, state="queued", job=job)


@transaction.atomic
def schedule_due_automation(identifier, now):
    snapshot = SourceAutomation.objects.get(pk=identifier)
    actor = User.objects.select_for_update(no_key=True).get(pk=snapshot.run_as_id)
    automation = (
        SourceAutomation.objects.select_for_update(skip_locked=True)
        .filter(pk=identifier, enabled=True, next_run_at__lte=now)
        .first()
    )
    if automation is None:
        return None
    if automation.run_as_id != actor.pk:
        return None
    automation.run_as = actor
    due_at = automation.next_run_at
    missed = advance_automation(automation, now)
    return enqueue_occurrence(automation, due_at, missed)


def run_automation_tick(now=None):
    now = now or timezone.now()
    identifiers = (
        SourceAutomation.objects.filter(enabled=True, next_run_at__lte=now)
        .order_by("next_run_at", "id")
        .values_list("id", flat=True)[:SCHEDULER_BATCH_SIZE]
    )
    return [
        run
        for identifier in identifiers
        if (run := schedule_due_automation(identifier, now)) is not None
    ]
