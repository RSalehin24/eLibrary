from urllib.parse import urlparse

from django.conf import settings


DEFAULT_SOURCE_SITE_HOST = "www.example.com"
ARCHIVE_MAX_PAGES = 80
SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}


def get_source_site_host():
    return (
        getattr(settings, "SOURCE_SITE_HOST", "")
        or DEFAULT_SOURCE_SITE_HOST
    ).strip().lower()


def get_source_site_domain():
    host = get_source_site_host()
    if host.startswith("www."):
        return host[4:]
    return host


def get_source_site_fallback_hosts():
    return tuple(
        host.strip().lower()
        for host in (getattr(settings, "SOURCE_SITE_FALLBACK_HOSTS", []) or [])
        if str(host).strip()
    )


def get_catalog_url():
    host = get_source_site_host()
    return f"https://{host}/books/" if host else ""


def get_source_site_dns_resolvers():
    return tuple(
        str(resolver).strip()
        for resolver in (
            getattr(settings, "SOURCE_SITE_DNS_RESOLVERS", None)
            or ("1.1.1.1", "8.8.8.8")
        )
        if str(resolver).strip()
    )


def source_request_hosts(host=""):
    candidates = [
        str(host or "").strip().lower(),
        get_source_site_host(),
        *get_source_site_fallback_hosts(),
    ]
    ordered = []
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return tuple(ordered)


def replace_url_host(url, host):
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.path:
        return url
    return parsed._replace(netloc=host).geturl()


def is_name_resolution_failure(exc):
    return "name resolution" in str(exc).lower() or "gaierror" in str(exc).lower()

