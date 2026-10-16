from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.accounts.serializers.totp import TOTPSetupSerializer
from apps.accounts.session_security import rotate_account_sessions


def totp_status(user):
    devices = TOTPDevice.objects.filter(user=user)
    enabled = devices.filter(confirmed=True).exists()
    return {
        "enabled": enabled,
        "pending_setup": devices.filter(confirmed=False).exists(),
        "required": user.totp_required,
        "setup_required": user.totp_required and not enabled,
    }


def require_current_password(user, password):
    require_active_security_user(user)
    if not user.check_password(password):
        raise ValidationError({"current_password": "Current password is incorrect."})


def require_active_security_user(user):
    if not user.is_active:
        raise PermissionDenied("This account is disabled.")


@transaction.atomic
def start_totp_setup(user, password):
    user = User.objects.select_for_update().get(pk=user.pk)
    require_current_password(user, password)
    if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
        raise ValidationError(
            {"token": "Two-factor authentication is already enabled."}
        )
    device = (
        TOTPDevice.objects.filter(user=user, confirmed=False).order_by("pk").first()
    )
    if device is None:
        device = TOTPDevice.objects.create(
            user=user, name="reader-authenticator", confirmed=False
        )
    return TOTPSetupSerializer.from_device(device)


@transaction.atomic
def verify_pending_device(user, token):
    user = User.objects.select_for_update().get(pk=user.pk)
    require_active_security_user(user)
    device = (
        TOTPDevice.objects.select_for_update()
        .filter(user=user, confirmed=False)
        .order_by("pk")
        .first()
    )
    if device is None:
        raise ValidationError({"token": "Start two-factor setup before confirming."})
    if not device.verify_token(token):
        return None
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    rotate_account_sessions(user)
    if user.email_setup_pending and user.has_usable_password():
        user.email_setup_pending = False
        user.save(update_fields=["email_setup_pending", "updated_at"])
    return device


def confirm_totp_setup(user, token):
    # Verification failures must commit the device's throttle counters.
    device = verify_pending_device(user, token)
    if device is None:
        raise ValidationError(
            {"token": "Code verification failed. Wait before trying again."}
        )
    return device


@transaction.atomic
def cancel_totp_setup(user):
    user = User.objects.select_for_update().get(pk=user.pk)
    require_active_security_user(user)
    TOTPDevice.objects.filter(user=user, confirmed=False).delete()


@transaction.atomic
def verify_and_disable_totp(user, values):
    user = User.objects.select_for_update().get(pk=user.pk)
    require_current_password(user, values["current_password"])
    if user.totp_required:
        raise ValidationError(
            {"token": "Your administrator requires two-factor authentication."}
        )
    devices = (
        TOTPDevice.objects.select_for_update()
        .filter(user=user, confirmed=True)
        .order_by("pk")
    )
    if not devices.exists():
        raise ValidationError({"token": "Two-factor authentication is not enabled."})
    for device in devices:
        if device.verify_token(values["token"]):
            TOTPDevice.objects.filter(user=user).delete()
            rotate_account_sessions(user)
            return True
    return False


def disable_totp(user, values):
    if not verify_and_disable_totp(user, values):
        raise ValidationError(
            {"token": "Code verification failed. Wait before trying again."}
        )
