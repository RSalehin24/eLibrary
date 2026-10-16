from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.mail_configuration import kindle_sender_email
from apps.accounts.serializers.support import password_link_token_generator
from apps.delivery.mail_transport import TextMessage
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def frontend_origin():
    origin = str(settings.FRONTEND_BASE_URL or "").rstrip("/")
    try:
        URLValidator(schemes=["http", "https"])(origin)
        url = urlsplit(origin)
        local_http = url.scheme == "http" and url.hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
        }
        valid = (
            (url.scheme == "https" or local_http)
            and url.hostname
            and not (
                url.username or url.password or url.path or url.query or url.fragment
            )
            and (url.port is None or 1 <= url.port <= 65535)
        )
    except (ValueError, ValidationError):
        valid = False
    if not valid or any(character.isspace() for character in origin):
        raise ExecutionFailure(FailureKind.PERMANENT, "mail_frontend_origin_invalid")
    return origin


def account_link(user, action):
    fragment = urlencode(
        {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": password_link_token_generator.make_token(user),
        }
    )
    path = "/reset-password/confirm/" if action == "reset" else "/create-password/"
    return f"{frontend_origin()}{path}#{fragment}"


def account_message(user, action):
    sender = kindle_sender_email()
    try:
        validate_email(sender)
        validate_email(user.email)
    except ValidationError:
        raise ExecutionFailure(FailureKind.PERMANENT, "message_invalid") from None
    subject = (
        "পাসওয়ার্ড পরিবর্তনের অনুরোধ" if action == "reset" else "আপনার বাংলা পাঠাগারের আমন্ত্রণ"
    )
    hours = max(1, int(settings.PASSWORD_RESET_TIMEOUT) // 3600)
    body = (
        f"{subject}\n\n{account_link(user, action)}\n\n"
        f"লিংকটি {hours} ঘণ্টার মধ্যে ব্যবহার করুন। নতুন লিংক চাইলে পুরোনোটি বন্ধ হয়ে যাবে।\n"
        "এই অনুরোধ আপনি না করে থাকলে ইমেইলটি উপেক্ষা করুন।"
    )
    return TextMessage(subject, sender, user.email, body)
