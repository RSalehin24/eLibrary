from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.common.validation import reject_unknown_fields
from apps.processing.automation_models import AutomationRun, SourceAutomation
from apps.processing.jobs.requests import JobStateConflict, require_processing_manager

from .scheduler import enqueue_occurrence


class AutomationRunCommandSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    expected_updated_at = serializers.DateTimeField()

    def validate(self, attrs):
        reject_unknown_fields(self)
        return attrs


class AutomationRunAcceptedSerializer(serializers.Serializer):
    run_id = serializers.UUIDField()
    job_id = serializers.UUIDField(allow_null=True)
    state = serializers.ChoiceField(choices=("queued", "blocked"))
    error_code = serializers.CharField(allow_blank=True)


def existing_manual_run(actor, automation, command):
    receipt = AuditLog.objects.filter(pk=command["operation_id"]).first()
    if receipt is None:
        return None
    if (
        receipt.actor_id != actor.pk
        or receipt.verb != "automation.run"
        or receipt.target_type != automation._meta.label_lower
        or receipt.target_id != str(automation.pk)
        or receipt.payload.get("revision") != command["expected_updated_at"].isoformat()
    ):
        raise JobStateConflict("This operation identifier belongs to another request.")
    return get_object_or_404(
        AutomationRun, pk=receipt.payload["run_id"], automation=automation
    )


def persist_manual_run(actor, automation, command):
    due_at = timezone.now()
    if (
        due_at == automation.next_run_at
        or automation.runs.filter(due_at=due_at).exists()
    ):
        raise JobStateConflict("A run already exists at this time. Refresh its status.")
    try:
        with transaction.atomic():
            run = enqueue_occurrence(automation, due_at, 0)
            AuditLog.objects.create(
                id=command["operation_id"],
                actor=actor,
                verb="automation.run",
                target_type=automation._meta.label_lower,
                target_id=str(automation.pk),
                payload={
                    "run_id": str(run.pk),
                    "revision": command["expected_updated_at"].isoformat(),
                },
            )
            return run
    except IntegrityError as error:
        previous = existing_manual_run(actor, automation, command)
        if previous is not None:
            return previous
        raise JobStateConflict(
            "A run was created concurrently. Refresh its status."
        ) from error


@transaction.atomic
def request_automation_run(actor, identifier, values):
    snapshot = get_object_or_404(SourceAutomation, pk=identifier)
    accounts = {
        user.pk: user
        for user in User.objects.select_for_update(no_key=True)
        .filter(pk__in=(actor.pk, snapshot.run_as_id))
        .order_by("pk")
    }
    actor = accounts[actor.pk]
    require_processing_manager(actor)
    automation = get_object_or_404(
        SourceAutomation.objects.select_for_update(), pk=identifier
    )
    if automation.run_as_id != snapshot.run_as_id:
        raise JobStateConflict()
    automation.run_as = accounts[automation.run_as_id]
    parameters = AutomationRunCommandSerializer(data=values)
    parameters.is_valid(raise_exception=True)
    command = parameters.validated_data
    previous = existing_manual_run(actor, automation, command)
    if previous is not None:
        return previous
    if automation.updated_at != command["expected_updated_at"]:
        raise JobStateConflict()
    return persist_manual_run(actor, automation, command)
