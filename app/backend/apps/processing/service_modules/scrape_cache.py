"""Disk-backed page cache for resumable book scraping.

When a large book scrape is interrupted mid-way (e.g. because the Celery
processing worker is restarted by Docker Compose watch, a deploy, or a
memory limit), this module lets the next attempt skip pages that were
already fetched and saved to disk.

Each content item (chapter HTML + metadata) is written to a per-request
JSONL file under ``<RUNTIME_STORAGE_DIR>/processing/scrape_cache/`` as
soon as it is fetched.  On the next run the cached items are loaded and
injected directly into the content-item list, so only the remaining
unvisited pages need to be fetched from the network.

The cache file is deleted automatically after a successful book creation.
"""

import json
import logging
from pathlib import Path

from django.conf import settings

_scrape_cache_logger = logging.getLogger(__name__)

_SCRAPE_CACHE_SUBDIR = "processing/scrape_cache"


def _get_scrape_cache_root():
    """Return (and create) the directory that holds per-request cache files."""
    base = getattr(settings, "RUNTIME_STORAGE_DIR", None)
    if base is None:
        import tempfile
        fallback = Path(tempfile.gettempdir()) / _SCRAPE_CACHE_SUBDIR
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    cache_root = Path(base) / _SCRAPE_CACHE_SUBDIR
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def scrape_cache_path_for_request(request_id):
    """Return the JSONL cache file path for a processing request.

    The ``request-`` prefix (if present) is stripped so the filename is a
    plain UUID, which is safe on all filesystems.
    """
    clean_id = str(request_id).replace("request-", "")
    return _get_scrape_cache_root() / f"{clean_id}.jsonl"


class DiskPageCache:
    """Append-only JSONL file cache for individual scraped content items.

    Usage::

        cache = DiskPageCache(scrape_cache_path_for_request(request_id))
        # Pass to curate_book() — it will save each page and resume on restart.

    Thread / process safety: only a single Celery worker uses a given request
    cache file at a time (processing concurrency = 1), so no locking is needed.
    """

    def __init__(self, path):
        self.path = Path(path)
        self._index = None  # lazily loaded; maps source_url -> item dict

    # ------------------------------------------------------------------
    # Internal

    def _load(self):
        if self._index is not None:
            return
        self._index = {}
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    url = (item or {}).get("source_url") or ""
                    if url:
                        self._index[url] = item
        except OSError:
            _scrape_cache_logger.warning(
                "Could not read scrape cache at %s — starting fresh.", self.path
            )
            self._index = {}

    # ------------------------------------------------------------------
    # Public API

    def has_cached_pages(self):
        """Return True if the cache file exists and contains at least one item."""
        self._load()
        return bool(self._index)

    def cached_count(self):
        """Return the number of cached page items."""
        self._load()
        return len(self._index)

    def has_url(self, url):
        """Return True if this URL was already fetched and persisted."""
        self._load()
        return url in self._index

    def get_cached_items(self):
        """Return a copy of {source_url: item} for all cached items."""
        self._load()
        return dict(self._index)

    def save_item(self, item):
        """Append a content item to the cache file.

        Items without a ``source_url`` are silently ignored.  I/O errors are
        logged as warnings rather than raised so a transient disk problem does
        not abort the entire scrape.
        """
        url = (item or {}).get("source_url") or ""
        if not url:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
            if self._index is not None:
                self._index[url] = item
        except OSError:
            _scrape_cache_logger.warning(
                "Could not save scrape cache item (url=%s) to %s.",
                url,
                self.path,
            )

    def delete(self):
        """Remove the cache file after successful book creation."""
        try:
            if self.path.exists():
                self.path.unlink()
                _scrape_cache_logger.debug("Deleted scrape cache %s.", self.path)
        except OSError:
            _scrape_cache_logger.debug(
                "Could not delete scrape cache %s.", self.path
            )
