import time
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    )
}

ALLOWED_SOURCE_HOSTS = {"ebanglalibrary.com", "www.ebanglalibrary.com"}


def normalize_source_url(url):
    """Normalize externally supplied ebanglalibrary book URLs."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Book URL must start with http:// or https://")
    if parsed.netloc.lower() not in ALLOWED_SOURCE_HOSTS:
        raise ValueError("Only ebanglalibrary.com book URLs are allowed")
    if not parsed.path.startswith("/books/"):
        raise ValueError("Only direct ebanglalibrary book URLs are supported")

    normalized_path = parsed.path.rstrip("/") + "/"
    return urlunparse(("https", "www.ebanglalibrary.com", normalized_path, "", "", ""))


def create_session_with_retries(retries=3, backoff_factor=1):
    """Create a requests session with automatic retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        read=0,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def decode_html_response(response):
    raw_content = getattr(response, "content", b"")
    if isinstance(raw_content, str):
        return raw_content
    if not raw_content:
        return getattr(response, "text", "")

    encoding = (
        getattr(response, "encoding", None)
        or requests.utils.get_encoding_from_headers(getattr(response, "headers", {}) or {})
        or getattr(response, "apparent_encoding", None)
        or "utf-8"
    )
    try:
        return raw_content.decode(encoding, errors="replace")
    except (AttributeError, LookupError, TypeError):
        return raw_content.decode("utf-8", errors="replace")


def get_soup(url, max_retries=3):
    """Fetch URL and return BeautifulSoup object with retry logic."""
    from apps.ingestion.services.resolution_support_network import get_with_host_fallback

    session = create_session_with_retries(retries=max_retries)
    try:
        for attempt in range(max_retries):
            try:
                response = get_with_host_fallback(
                    session,
                    url,
                    headers=HEADERS,
                    timeout=30,
                )
                if response.status_code == 200:
                    return BeautifulSoup(decode_html_response(response), "html.parser")
                print(f"Failed to fetch {url} ({response.status_code})")
                return None
            except requests.exceptions.SSLError as error:
                print(f"SSL Error (attempt {attempt + 1}/{max_retries}): {error}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
            except requests.exceptions.RequestException as error:
                print(f"Request error (attempt {attempt + 1}/{max_retries}): {error}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
    finally:
        close = getattr(session, "close", None)
        if callable(close):
            close()

    print(f"Failed to fetch {url} after {max_retries} attempts")
    return None


def login_source_session(session):
    """Load ebanglalibrary.com auth cookies from a saved session-state file.

    The state file is generated once by running ``local/scripts/save_ebangla_auth.py``
    on a local machine (which reads the wordpress_logged_in_* cookie straight out
    of the developer's logged-in browser, since Cloudflare blocks automated
    logins), then placed in ``app/backend/storage/`` which is mounted into all
    Docker containers.

    Configure via the ``EBANGLA_AUTH_STATE_PATH`` env var (defaults to
    ``{RUNTIME_STORAGE_DIR}/ebangla_auth.json`` when that env var is set, or
    leave empty to skip authentication entirely).

    Mutates ``session`` in-place with the resulting auth cookies.
    Returns True when at least one auth cookie was loaded.
    """
    import json
    import logging
    import os

    logger = logging.getLogger(__name__)

    from django.conf import settings

    state_path = (getattr(settings, "EBANGLA_AUTH_STATE_PATH", "") or "").strip()
    if not state_path:
        logger.debug(
            "EBANGLA_AUTH_STATE_PATH not set; ebanglalibrary.com auth skipped."
        )
        return False

    if not os.path.exists(state_path):
        logger.warning(
            "EBANGLA_AUTH_STATE_PATH=%r but the file does not exist. "
            "Run local/scripts/save_ebangla_auth.py to generate it, "
            "then for EC2: scp app/backend/storage/ebangla_auth.json "
            "ubuntu@<EC2_IP>:~/library_app/app/backend/storage/",
            state_path,
        )
        return False

    try:
        with open(state_path) as f:
            state = json.load(f)
    except (OSError, ValueError) as exc:
        logger.warning("Failed to read ebangla auth state from %r: %s", state_path, exc)
        return False

    domain_cookies = [
        c
        for c in state.get("cookies", [])
        if c.get("domain", "").lstrip(".") in ("ebanglalibrary.com", "www.ebanglalibrary.com")
        and c.get("name")
    ]

    has_login_cookie = any(
        c["name"].startswith("wordpress_logged_in_") for c in domain_cookies
    )
    if not has_login_cookie:
        logger.warning(
            "No wordpress_logged_in_* cookies found in %r. "
            "Re-run local/scripts/save_ebangla_auth.py to refresh the auth state.",
            state_path,
        )
        return False

    for c in domain_cookies:
        session.cookies.set(c["name"], c.get("value", ""), domain="www.ebanglalibrary.com")

    logger.debug(
        "Loaded %d ebanglalibrary.com cookie(s) from state file.",
        len(domain_cookies),
    )
    return True


def clean_buttons(soup):
    for button in soup.find_all("button"):
        button.decompose()
    return soup
