from typing import Protocol, cast

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User


class OTPVerifiedUser(Protocol):
    otp_device: TOTPDevice | None


def attach_verified_device(user: AbstractBaseUser, device: TOTPDevice):
    # django-otp's login signal reads this documented, dynamically added field.
    cast(OTPVerifiedUser, user).otp_device = device


@transaction.atomic
def verify_login_token(user, token):
    User.objects.select_for_update().get(pk=user.pk)
    device = (
        TOTPDevice.objects.select_for_update()
        .filter(user=user, confirmed=True)
        .order_by("pk")
        .first()
    )
    return device if device is not None and device.verify_token(token) else None
