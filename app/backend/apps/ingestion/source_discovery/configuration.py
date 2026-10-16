import json
from hashlib import sha256

from django.conf import settings

from apps.ingestion.source_processing.policy import require_source_url, source_hosts

MAX_DISCOVERY_PAGES = 200
DEFAULT_DISCOVERY_PAGES = 20
MAX_PAGE_ENTRIES = 1000


def discovery_configuration():
    hosts = source_hosts()
    url = (
        settings.SOURCE_SITE_CATALOG_URL
        or f"https://{settings.SOURCE_SITE_HOST}/books/"
    )
    require_source_url(url, hosts)
    revision = sha256(
        json.dumps({"url": url, "hosts": sorted(hosts)}, sort_keys=True).encode()
    ).hexdigest()
    return {"catalog_url": url, "configuration_revision": revision}
