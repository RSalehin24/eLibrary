from hashlib import sha256

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.management_access.policy import AccessConflict
from apps.processing.job_models import BackgroundJob, BackgroundJobKind, JobDispatch


def link_revision(user):
    state = (
        user.password,
        user.email,
        user.last_login,
        user.password_setup_nonce,
        user.email_setup_pending,
    )
    return sha256(repr(state).encode()).hexdigest()


def existing_command(actor, identifier, values):
    existing = BackgroundJob.objects.filter(pk=identifier).first()
    if existing is None:
        return None
    if (
        existing.kind != BackgroundJobKind.ACCOUNT_MAIL
        or existing.requested_by_id != actor.pk
        or existing.input.get("command") != values
    ):
        raise AccessConflict("This operation identifier belongs to another request.")
    return existing


@transaction.atomic
def persist_mail_job(target, actor, command):
    identifier, values = command
    job = BackgroundJob.objects.create(
        id=identifier,
        account=target,
        requested_by=actor,
        kind=BackgroundJobKind.ACCOUNT_MAIL,
        available_at=timezone.now(),
        input={"command": values, "link_revision": link_revision(target)},
    )
    JobDispatch.objects.create(
        job=job, generation=job.generation, available_at=job.available_at
    )
    return job


def enqueue_mail_job(target, actor, command):
    try:
        return persist_mail_job(target, actor, command)
    except IntegrityError as error:
        if actor is None:
            raise
        existing = existing_command(actor, *command)
        if existing is None:
            raise AccessConflict("The operation could not be created.") from error
        return existing
