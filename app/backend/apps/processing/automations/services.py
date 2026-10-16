from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.processing.automation_models import SourceAutomation
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .serializers import AutomationCreateSerializer, AutomationUpdateSerializer


def record_automation_change(actor, automation, action):
    AuditLog.objects.create(
        actor=actor,
        verb=f"automation.{action}",
        target_type=automation._meta.label_lower,
        target_id=str(automation.pk),
    )


def automation_values(cleaned):
    return {
        key: value
        for key, value in cleaned.items()
        if key not in {"first_run_local", "operation_id", "expected_updated_at"}
    }


def matching_automation(actor, identifier, values):
    existing = SourceAutomation.objects.filter(pk=identifier).first()
    if existing is None:
        return None
    if existing.run_as_id != actor.pk or any(
        getattr(existing, field) != value for field, value in values.items()
    ):
        raise JobStateConflict("This request identifier belongs to another schedule.")
    return existing


@transaction.atomic
def create_automation(actor, values):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    identifier = AutomationCreateSerializer().to_internal_value(values)["operation_id"]
    previous = SourceAutomation.objects.filter(pk=identifier).first()
    parameters = AutomationCreateSerializer(
        data=values, context={"automation": previous}
    )
    parameters.is_valid(raise_exception=True)
    cleaned = parameters.validated_data
    identifier, fields = cleaned["operation_id"], automation_values(cleaned)
    existing = matching_automation(actor, identifier, fields)
    if existing is not None:
        return existing
    try:
        with transaction.atomic():
            automation = SourceAutomation.objects.create(
                id=identifier,
                run_as=actor,
                next_run_at=fields["first_run_at"],
                **fields,
            )
    except IntegrityError:
        existing = matching_automation(actor, identifier, fields)
        if existing is None:
            raise
        return existing
    record_automation_change(actor, automation, "create")
    return automation


@transaction.atomic
def update_automation(actor, identifier, values):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_processing_manager(actor)
    automation = get_object_or_404(
        SourceAutomation.objects.select_for_update(), pk=identifier
    )
    parameters = AutomationUpdateSerializer(
        data=values, context={"automation": automation}
    )
    parameters.is_valid(raise_exception=True)
    cleaned = parameters.validated_data
    if automation.updated_at != cleaned["expected_updated_at"]:
        raise JobStateConflict()
    fields = automation_values(cleaned)
    if any(
        getattr(automation, field) != fields[field]
        for field in ("first_run_at", "time_zone", "frequency")
    ):
        automation.next_run_at, automation.occurrence_number = fields["first_run_at"], 0
    for key, value in fields.items():
        setattr(automation, key, value)
    automation.run_as = actor
    automation.save()
    record_automation_change(actor, automation, "update")
    return automation
