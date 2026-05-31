#!/usr/bin/env python3
"""Save ebanglalibrary.com session cookies for the backend scraper.

Why this exists
---------------
Multi-page book tables of contents (LearnDash pagination, pages 2+) can only be
fetched from an *authenticated* session.  The login form posts to a Cloudflare
"managed challenge" endpoint that blocks every automated browser (headless or
headed, bundled Chromium or real Chrome, with or without stealth patches).  The
only thing Cloudflare lets through is a genuine human browser session.

So instead of automating the login we simply *reuse the cookies from the real
browser the user is already logged into*.  Log in once on ebanglalibrary.com in
**Firefox** (tick "Remember Me" so the WordPress cookie lasts ~1 year), then
run this script.  It reads the ``wordpress_logged_in_*`` cookie straight out of
Firefox's cookie store and writes it to
``app/backend/storage/ebangla_auth.json`` which is mounted into every Docker
container.  The backend loads it on demand — no live login ever happens inside
Docker or on EC2.

Usage
-----
    bash local/scripts/save-ebangla-auth.sh      # preferred (handles deps)
    # or directly:
    python local/scripts/save_ebangla_auth.py

If no logged-in cookie can be read automatically (e.g. the browser keychain
prompt is declined, or you are on a headless box), the script falls back to a
manual paste mode: open DevTools on ebanglalibrary.com, copy the
``wordpress_logged_in_*`` cookie, and paste it in.

Output
------
    app/backend/storage/ebangla_auth.json

Re-run whenever scraping stops returning pages 2+ (i.e. the cookie expired).
"""

import datetime
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_FILE = REPO_ROOT / "app" / "backend" / "storage" / "ebangla_auth.json"
DOMAIN = "ebanglalibrary.com"
COOKIE_DOMAIN = "www.ebanglalibrary.com"
AUTH_PREFIX = "wordpress_logged_in_"


def _to_state_cookie(name, value, domain=COOKIE_DOMAIN, expires=None):
    """Build a Playwright-compatible storage-state cookie entry."""
    return {
        "name": name,
        "value": value,
        "domain": domain,
        "path": "/",
        "expires": float(expires) if expires else -1,
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
    }


def cookies_from_real_browsers():
    """Return (state_cookies, source_name) read from Firefox.

    Reads every cookie for ebanglalibrary.com from Firefox and returns the
    first profile that has a ``wordpress_logged_in_*`` cookie.
    Returns ([], None) when nothing is found / browser_cookie3 missing.
    """
    try:
        import browser_cookie3 as bc
    except ImportError:
        print(
            "(browser-cookie3 not installed; skipping automatic browser read.\n"
            " Install with:  pip install browser-cookie3)"
        )
        return [], None

    label = "Firefox"
    loader = getattr(bc, "firefox", None)
    if loader is None:
        print(f"  - {label}: not available in this version of browser-cookie3")
        return [], None

    print(f"  - {label}: reading cookies...")
    try:
        jar = loader(domain_name=DOMAIN)
    except Exception as exc:  # noqa: BLE001 - browser locked / not installed
        print(f"  - {label}: skipped ({str(exc)[:70]})")
        return [], None

    cookies = [c for c in jar if DOMAIN in (c.domain or "")]
    if not cookies:
        print(f"  - {label}: no ebanglalibrary.com cookies found")
        return [], None

    has_auth = any((c.name or "").startswith(AUTH_PREFIX) for c in cookies)
    if not has_auth:
        print(f"  - {label}: cookies present but not logged in")
        return [], None

    state_cookies = [
        _to_state_cookie(
            c.name,
            c.value,
            domain=(c.domain or COOKIE_DOMAIN).lstrip("."),
            expires=c.expires,
        )
        for c in cookies
    ]
    print(f"  - {label}: found logged-in session ({len(state_cookies)} cookie(s))")
    return state_cookies, label


def cookies_from_manual_paste():
    """Prompt the user to paste the auth cookie from DevTools."""
    if not sys.stdin.isatty():
        return []

    print(
        "\n"
        "------------------------------------------------------------\n"
        " Manual cookie entry\n"
        "------------------------------------------------------------\n"
        " 1. Open https://www.ebanglalibrary.com in your browser and\n"
        "    make sure you are logged in (tick 'Remember Me').\n"
        " 2. Open DevTools (F12) -> Application/Storage -> Cookies ->\n"
        "    https://www.ebanglalibrary.com\n"
        " 3. Find the cookie whose name starts with\n"
        "    'wordpress_logged_in_' and copy its NAME and VALUE.\n"
        "------------------------------------------------------------\n"
    )
    name = input("Cookie NAME (wordpress_logged_in_...): ").strip()
    if not name.startswith(AUTH_PREFIX):
        print(f"Error: name must start with '{AUTH_PREFIX}'.")
        return []
    value = input("Cookie VALUE: ").strip()
    if not value:
        print("Error: empty value.")
        return []
    return [_to_state_cookie(name, value)]


def main() -> None:
    if os.environ.get("EBANGLA_SKIP_BROWSER_READ", "").strip() in ("1", "true", "yes"):
        print("EBANGLA_SKIP_BROWSER_READ set — using manual paste mode.")
        state_cookies = cookies_from_manual_paste()
        source = "manual paste" if state_cookies else None
    else:
        print("Reading ebanglalibrary.com session from Firefox...")
        state_cookies, source = cookies_from_real_browsers()

        if not state_cookies:
            print("\nNo logged-in browser session found automatically.")
            state_cookies = cookies_from_manual_paste()
            source = "manual paste" if state_cookies else None

    auth_cookies = [c for c in state_cookies if c["name"].startswith(AUTH_PREFIX)]
    if not auth_cookies:
        print(
            "\nError: could not obtain a 'wordpress_logged_in_*' cookie.\n"
            "Log in to https://www.ebanglalibrary.com in your browser (tick\n"
            "'Remember Me') and re-run this script."
        )
        sys.exit(1)

    state = {"cookies": state_cookies, "origins": []}
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    print(f"\nSaved auth state ({source}) -> {OUTPUT_FILE}")
    print(f"Found {len(auth_cookies)} auth cookie(s):")
    for c in auth_cookies:
        expires = c.get("expires", -1)
        if expires and expires > 0:
            try:
                exp_dt = datetime.datetime.fromtimestamp(expires)
                print(f"  {c['name'][:60]}  (expires {exp_dt.strftime('%Y-%m-%d')})")
            except (ValueError, OverflowError, OSError):
                print(f"  {c['name'][:60]}  (expires far in the future)")
        else:
            print(f"  {c['name'][:60]}  (session cookie, no expiry)")

    print(
        "\nLocal Docker picks this up automatically (storage/ is bind-mounted).\n"
        "For EC2 it is synced automatically on the next deploy/scripts/deploy.sh run."
    )
    print("\nDone.")


if __name__ == "__main__":
    main()
