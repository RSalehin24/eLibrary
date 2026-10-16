from datetime import timedelta
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.management_access.policy import (
    AccessConflict,
    require_access_manager,
    require_revision,
)
from apps.accounts.management_access.services import locked_accounts, record_change
from apps.accounts.models import User

from .commands import enqueue_mail_job, existing_command
from .serializers import InvitationSerializer, ResendInvitationSerializer

RESET_COOLDOWN_SECONDS = 300


def create_invited_account(values):
    if User.objects.filter(email__iexact=values["email"]).exists():
        raise ValidationError({"email": "An account already uses this email address."})
    try:
        with transaction.atomic():
            return User.objects.create_user(**values, email_setup_pending=True)
    except IntegrityError as error:
        raise AccessConflict(
            "An account was created concurrently. Refresh the list."
        ) from error


@transaction.atomic
def request_invitation(actor, values):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    require_access_manager(actor)
    serializer = InvitationSerializer(data=values)
    serializer.is_valid(raise_exception=True)
    cleaned = dict(serializer.validated_data)
    identifier = cleaned.pop("operation_id")
    command = {"action": "invite", **cleaned}
    existing = existing_command(actor, identifier, command)
    if existing is not None:
        return existing
    target = create_invited_account(cleaned)
    job = enqueue_mail_job(target, actor, (identifier, command))
    record_change(actor, target, "account.invite")
    return job


@transaction.atomic
def request_invitation_resend(actor, identifier, values):
    target = locked_accounts(actor, identifier)
    serializer = ResendInvitationSerializer(data=values)
    serializer.is_valid(raise_exception=True)
    cleaned = serializer.validated_data
    command = {
        "action": "resend",
        "account_id": target.pk,
        "expected_updated_at": cleaned["expected_updated_at"].isoformat(),
    }
    existing = existing_command(actor, cleaned["operation_id"], command)
    if existing is not None:
        return existing
    require_revision(target, cleaned["expected_updated_at"])
    if not target.can_resend_setup_email:
        raise AccessConflict("This account does not need an invitation email.")
    target.password_setup_nonce += 1
    target.save(update_fields=["password_setup_nonce", "updated_at"])
    job = enqueue_mail_job(target, actor, (cleaned["operation_id"], command))
    record_change(actor, target, "account.invite_resend")
    return job


@transaction.atomic
def request_password_reset(email):
    target = (
        User.objects.select_for_update(no_key=True)
        .filter(email__iexact=email, is_active=True)
        .order_by("pk")
        .first()
    )
    if target is None or target.email_setup_pending or not target.has_usable_password():
        return
    cutoff = timezone.now() - timedelta(seconds=RESET_COOLDOWN_SECONDS)
    if target.account_mail_jobs.filter(
        input__command__action="reset", created_at__gte=cutoff
    ).exists():
        return
    target.password_setup_nonce += 1
    target.save(update_fields=["password_setup_nonce", "updated_at"])
    enqueue_mail_job(target, None, (uuid4(), {"action": "reset"}))
