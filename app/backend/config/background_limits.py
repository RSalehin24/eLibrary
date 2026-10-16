from collections.abc import Callable

from django.core.exceptions import ImproperlyConfigured

DEFAULT_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 128 * 1024 * 1024


def background_limits(environment: Callable[[str, int], int]) -> tuple[int, int]:
    timeout = environment("BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS", 3600)
    attachment = environment("KINDLE_MAX_ATTACHMENT_BYTES", DEFAULT_ATTACHMENT_BYTES)
    if not 1024 <= attachment <= MAX_ATTACHMENT_BYTES:
        raise ImproperlyConfigured(
            "KINDLE_MAX_ATTACHMENT_BYTES must be between 1024 and 134217728."
        )
    if not 60 <= timeout <= 86400:
        raise ImproperlyConfigured(
            "BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS must be between 60 and 86400."
        )
    return timeout, attachment
