from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

KINDLE_EMAIL_DOMAINS = {"kindle.com"}
KINDLE_EMAIL_DOMAIN_MESSAGE = "Enter a Kindle email ending in @kindle.com."


def validate_kindle_email_address(value):
    email = str(value or "").strip().lower()
    try:
        validate_email(email)
    except DjangoValidationError as exc:
        raise DjangoValidationError(list(exc.messages)) from exc

    domain = email.rsplit("@", 1)[-1].lower()
    if domain not in KINDLE_EMAIL_DOMAINS:
        raise DjangoValidationError([KINDLE_EMAIL_DOMAIN_MESSAGE])

    return email
