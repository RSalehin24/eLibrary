from email.utils import parseaddr

from django.conf import settings

BREVO_EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
SMTP_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_CONSOLE_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
BREVO_SMTP_PORT = 587


def resolve_kindle_delivery_email_backend():
    primary_backend = str(getattr(settings, "EMAIL_BACKEND", "") or "").strip()
    if primary_backend == BREVO_EMAIL_BACKEND:
        # The Brevo API cannot carry the existing EPUB attachment workflow.
        return SMTP_EMAIL_BACKEND
    return primary_backend or DEFAULT_CONSOLE_EMAIL_BACKEND


def configured_boolean(value, *, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


def configured_integer(value, *, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def smtp_connection_parameters():
    return {
        "host": str(getattr(settings, "EMAIL_HOST", "") or "").strip(),
        "port": configured_integer(
            getattr(settings, "EMAIL_PORT", BREVO_SMTP_PORT), default=BREVO_SMTP_PORT
        ),
        "username": str(getattr(settings, "EMAIL_HOST_USER", "") or "").strip(),
        "password": str(getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip(),
        "use_tls": configured_boolean(
            getattr(settings, "EMAIL_USE_TLS", True), default=True
        ),
        "use_ssl": configured_boolean(
            getattr(settings, "EMAIL_USE_SSL", False), default=False
        ),
        "timeout": configured_integer(
            getattr(settings, "EMAIL_TIMEOUT", 20), default=20
        ),
    }


def build_kindle_delivery_connection_kwargs():
    backend = resolve_kindle_delivery_email_backend()
    kwargs = {"backend": backend}
    if backend == SMTP_EMAIL_BACKEND:
        kwargs.update(smtp_connection_parameters())
    return kwargs


def build_kindle_delivery_connection_attempts():
    return [build_kindle_delivery_connection_kwargs()]


def kindle_sender_email() -> str:
    raw_email = (
        getattr(settings, "ACCOUNT_INVITE_FROM_EMAIL", "")
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        or ""
    ).strip("'\" ")
    return parseaddr(raw_email)[1]
