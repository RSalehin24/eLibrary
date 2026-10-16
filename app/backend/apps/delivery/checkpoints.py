from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import UserBookKindleSend
from apps.delivery.job_data import accepted_recipient_indices
from apps.processing.job_models import JobAttempt
from apps.processing.jobs.attempts import (
    complete_attempt,
    owned_job,
    settle_requested_action,
)


@transaction.atomic
def record_mail_acceptance(ownership, actor_id, index):
    actor = User.objects.select_for_update(no_key=True).filter(pk=actor_id).first()
    job = owned_job(ownership)
    accepted = accepted_recipient_indices(job) | {index}
    checkpoint = {**job.checkpoint, "accepted": sorted(accepted)}
    checkpoint.pop("sending_index", None)
    checkpoint.pop("rejected_index", None)
    checkpoint.pop("rejection_code", None)
    job.checkpoint = checkpoint
    job.save(update_fields=["checkpoint", "updated_at"])
    JobAttempt.objects.filter(pk=ownership.attempt_id).update(
        stage="accepted", heartbeat_at=timezone.now()
    )
    if actor is not None:
        UserBookKindleSend.objects.update_or_create(
            user=actor, book=job.book, defaults={"created_at": timezone.now()}
        )
    if len(accepted) == len(job.input["recipients"]):
        complete_attempt(ownership)
        return False
    stopped = settle_requested_action(job)
    if stopped:
        JobAttempt.objects.filter(pk=ownership.attempt_id).update(
            finished_at=timezone.now()
        )
    return not stopped
