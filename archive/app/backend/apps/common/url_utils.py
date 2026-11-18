from urllib.parse import urljoin
from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse


def public_api_url(viewname, *, kwargs=None, request=None):
    path = reverse(viewname, kwargs=kwargs)
    public_origin = getattr(settings, "PUBLIC_API_ORIGIN", "").rstrip("/")
    if public_origin and not _is_loopback_origin(public_origin):
        return urljoin(f"{public_origin}/", path.lstrip("/"))
    if request is not None:
        return request.build_absolute_uri(path)
    if public_origin:
        return urljoin(f"{public_origin}/", path.lstrip("/"))
    return path


def _is_loopback_origin(origin):
    parsed = urlparse((origin or "").strip())
    host = (parsed.hostname or "").strip().lower()
    return host in {"localhost", "127.0.0.1", "::1"}
