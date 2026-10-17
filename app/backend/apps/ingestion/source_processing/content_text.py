from unicodedata import normalize

from apps.ingestion.services.normalization import plain_text_from_html


def canonical_text(html):
    return normalize("NFC", " ".join(plain_text_from_html(html).split()))
