import json
import os


def _normalize_entry(entry):
    if isinstance(entry, (list, tuple)) and len(entry) == 2:
        return str(entry[0]), str(entry[1])
    if isinstance(entry, dict):
        name = str(entry.get("name") or entry.get("title") or entry.get("url") or "").strip()
        url = str(entry.get("url") or "").strip()
        if name and url:
            return name, url
    raise ValueError("Each BOOK_URLS entry must be a (name, url) pair or an object with `name` and `url`.")


def load_book_urls():
    raw_json = os.environ.get("BOOK_URLS_JSON", "").strip()
    if raw_json:
        payload = json.loads(raw_json)
        return [_normalize_entry(entry) for entry in payload]

    single_url = os.environ.get("BOOK_URL", "").strip()
    if single_url:
        single_name = os.environ.get("BOOK_NAME", single_url).strip()
        return [(single_name, single_url)]

    return []


BOOK_URLS = load_book_urls()
