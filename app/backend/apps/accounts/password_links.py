from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.http import urlsafe_base64_decode
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.accounts.serializers.support import password_link_token_generator


def invalid_password_link():
    return ValidationError({"token": "This password link is invalid or expired."})


def password_link_user_id(uid):
    try:
        decoded = urlsafe_base64_decode(uid).decode("ascii")
    except (ValueError, UnicodeError, OverflowError) as error:
        raise invalid_password_link() from error
    if not decoded.isdecimal() or len(decoded) > 19:
        raise invalid_password_link()
    return int(decoded)


def require_valid_password_link(user, token):
    if (
        user is None
        or not user.is_active
        or not password_link_token_generator.check_token(user, token)
    ):
        raise invalid_password_link()
    return user


def inspect_password_link(values):
    user = User.objects.filter(pk=password_link_user_id(values["uid"])).first()
    user = require_valid_password_link(user, values["token"])
    return {
        "purpose": "setup" if user.email_setup_pending else "reset",
        "totp_setup_required": user.requires_totp_setup,
    }


def validate_link_password(user, password):
    try:
        validate_password(password, user)
    except DjangoValidationError as error:
        raise ValidationError({"new_password": error.messages}) from error


@transaction.atomic
def confirm_password_link(values):
    user = (
        User.objects.select_for_update()
        .filter(pk=password_link_user_id(values["uid"]))
        .first()
    )
    user = require_valid_password_link(user, values["token"])
    validate_link_password(user, values["new_password"])
    user.set_password(values["new_password"])
    user.password_setup_nonce += 1
    user.email_setup_pending = user.requires_totp_setup
    user.save(
        update_fields=[
            "password",
            "password_setup_nonce",
            "email_setup_pending",
            "updated_at",
        ]
    )
    return user
