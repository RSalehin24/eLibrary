from hashlib import sha256

from django.db import connection

from apps.common.text import normalize_catalog_text


def lock_title(title):
    key = int.from_bytes(
        sha256(normalize_catalog_text(title).encode()).digest()[:8], signed=True
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])
