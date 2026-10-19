from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_SOURCE_CACHE_BYTES = 2 * 1024 * 1024 * 1024
MAX_DOCUMENT_BYTES = 64 * 1024 * 1024
MAX_SOURCE_PAGES = 2000
SENSITIVE_QUERY_PARTS = ("token", "secret", "password", "auth", "nonce", "key")


def sensitive_source_query(url):
    query = parse_qs(url.query)
    public_pager = (
        url.path == "/wp-admin/admin-ajax.php"
        and query.get("action") == ["ld30_ajax_pager"]
        and query.get("context") == ["course_content_shortcode"]
    )
    return any(
        part in key.lower()
        for key in query
        if not (public_pager and key == "pager_nonce")
        for part in SENSITIVE_QUERY_PARTS
    )


def source_hosts():
    host = str(settings.SOURCE_SITE_HOST).strip().lower()
    if not host:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_configuration_missing")
    allowed = frozenset([host, host[4:] if host.startswith("www.") else f"www.{host}"])
    if any(
        value.strip().lower() not in allowed
        for value in settings.SOURCE_SITE_FALLBACK_HOSTS
        if value.strip()
    ):
        raise ExecutionFailure(FailureKind.PERMANENT, "source_configuration_invalid")
    return allowed


def require_source_url(value, allowed):
    try:
        URLValidator(schemes=["https"])(value)
        url = urlsplit(value)
        invalid = (
            url.hostname not in allowed
            or url.port not in {None, 443}
            or url.username
            or url.password
            or url.fragment
        )
        sensitive = sensitive_source_query(url)
    except (ValueError, ValidationError):
        invalid, sensitive = True, True
    if invalid or sensitive:
        raise ExecutionFailure(FailureKind.PERMANENT, "source_url_not_allowed")
    return value
