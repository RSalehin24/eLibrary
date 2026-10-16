from apps.accounts.serializers.support import password_link_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

INSPECT = "/api/v1/auth/password-links/inspect/"
CONFIRM = "/api/v1/auth/password-links/confirm/"


def password_ticket(user):
    return {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": password_link_token_generator.make_token(user),
    }


def confirmation_values(user):
    password = "zQ7!mN4#vT9@xR2$wB6%"
    return {
        **password_ticket(user),
        "new_password": password,
        "confirm_new_password": password,
    }
