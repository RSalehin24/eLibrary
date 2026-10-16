import posixpath
import re
import unicodedata
from urllib.parse import unquote, urlsplit


class InvalidEpub(ValueError):
    pass


def resource_path(value: str) -> str:
    path = unicodedata.normalize("NFC", value)
    parts = path.split("/")
    if (
        not path
        or len(path) > 512
        or path.startswith("/")
        or "\\" in path
        or ":" in path
        or any(part in {"", ".", ".."} for part in parts)
        or re.search(r"[\x00-\x1f\x7f]", path)
    ):
        raise InvalidEpub("Invalid EPUB resource path.")
    return path


def referenced_path(base: str, value: str) -> str:
    reference = urlsplit(value)
    if reference.scheme or reference.netloc or reference.query:
        raise InvalidEpub("EPUB resources must use local paths.")
    decoded = unquote(reference.path, errors="strict")
    if decoded.startswith("/") or "\\" in decoded:
        raise InvalidEpub("Invalid EPUB resource reference.")
    path = posixpath.normpath(posixpath.join(posixpath.dirname(base), decoded))
    return resource_path(path)
