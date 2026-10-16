import json
import re
from pathlib import Path

from django.conf import settings

from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

MAX_AUTH_STATE_BYTES = 2 * 1024 * 1024
COOKIE_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


def read_source_cookies():
    configured = str(settings.SOURCE_SITE_AUTH_STATE_PATH or "")
    if not configured or not Path(configured).is_file():
        return []
    try:
        with Path(configured).open("rb") as handle:
            data = handle.read(MAX_AUTH_STATE_BYTES + 1)
        if len(data) > MAX_AUTH_STATE_BYTES:
            raise ValueError("Source authentication state exceeded its limit.")
        cookies = json.loads(data).get("cookies", [])
        if not isinstance(cookies, list) or len(cookies) > 100:
            raise ValueError("Invalid source cookies.")
        return cookies
    except (OSError, ValueError, AttributeError):
        raise ExecutionFailure(
            FailureKind.PERMANENT, "source_authentication_invalid"
        ) from None


def load_source_authentication(session):
    for cookie in read_source_cookies():
        if not isinstance(cookie, dict):
            raise ExecutionFailure(
                FailureKind.PERMANENT, "source_authentication_invalid"
            )
        domain = str(cookie.get("domain", "")).lstrip(".").lower()
        if domain not in session.allowed_hosts:
            continue
        name, value = cookie.get("name", ""), cookie.get("value", "")
        if (
            not isinstance(name, str)
            or not COOKIE_NAME.fullmatch(name)
            or not isinstance(value, str)
            or any(ord(character) < 32 or ord(character) > 126 for character in value)
        ):
            raise ExecutionFailure(
                FailureKind.PERMANENT, "source_authentication_invalid"
            )
        session.cookies.set(name, value, domain=domain, path="/", secure=True)
