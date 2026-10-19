from django.db import transaction
from django.http import Http404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.catalog.editorial.service import EditorialConflict
from apps.common.models import AuditLog
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.requests import (
    JobControlRequest,
    JobStateConflict,
    control_background_job,
    require_processing_manager,
)
from apps.processing.jobs.source_bulk_controls import (
    SOURCE_BULK_ACTIONS,
    control_source_job,
)


def control_outcome(actor, values, action):
    entry, _operation_id = values
    try:
        if action in SOURCE_BULK_ACTIONS:
            control_source_job(actor, values, action)
        else:
            control_background_job(
                actor,
                JobControlRequest(entry["id"], entry["expected_updated_at"], action),
            )
    except (JobStateConflict, EditorialConflict):
        return {"id": str(entry["id"]), "outcome": "conflict", "code": "state_conflict"}
    except Http404:
        return {"id": str(entry["id"]), "outcome": "not_found", "code": "not_found"}
    except PermissionDenied:
        return {
            "id": str(entry["id"]),
            "outcome": "forbidden",
            "code": "permission_denied",
        }
    except (ValidationError, ExecutionFailure):
        return {
            "id": str(entry["id"]),
            "outcome": "rejected",
            "code": "source_action_unavailable",
        }
    return {"id": str(entry["id"]), "outcome": "accepted", "code": ""}


def receipt_command(values):
    return {
        "action": values["action"],
        "entries": [
            {
                "id": str(entry["id"]),
                "expected_updated_at": entry["expected_updated_at"].isoformat(),
                **(
                    {
                        "expected_book_updated_at": entry[
                            "expected_book_updated_at"
                        ].isoformat()
                    }
                    if entry.get("expected_book_updated_at")
                    else {}
                ),
            }
            for entry in values["entries"]
        ],
    }


@transaction.atomic
def control_job_selection(actor, values):
    actor = User.objects.select_for_update().get(pk=actor.pk)
    require_processing_manager(actor)
    command = receipt_command(values)
    receipt, created = AuditLog.objects.get_or_create(
        pk=values["operation_id"],
        defaults={
            "actor": actor,
            "verb": "processing.jobs.bulk_control",
            "target_type": "processing.backgroundjob",
            "target_id": str(values["operation_id"]),
            "payload": {"command": command},
        },
    )
    if not created:
        if (
            receipt.actor_id != actor.pk
            or receipt.verb != "processing.jobs.bulk_control"
            or receipt.payload.get("command") != command
        ):
            raise JobStateConflict(
                "This request identifier belongs to another bulk command."
            )
        return receipt.payload["result"]
    result = {
        "operation_id": str(values["operation_id"]),
        "entries": [
            control_outcome(actor, (entry, values["operation_id"]), values["action"])
            for entry in values["entries"]
        ],
    }
    receipt.payload = {"command": command, "result": result}
    receipt.save(update_fields=["payload", "updated_at"])
    return result
