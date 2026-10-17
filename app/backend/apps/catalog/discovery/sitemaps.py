from math import ceil

from django.http import Http404

from apps.catalog.discovery.entities import public_entities
from apps.catalog.discovery.queries import published_books

SITEMAP_BATCH_SIZE = 1000
SITEMAP_KINDS = ("books", "contributors", "categories", "series", "collections")


def indexable_records(kind):
    if kind not in SITEMAP_KINDS:
        raise Http404
    queryset = published_books() if kind == "books" else public_entities(kind)
    return queryset.filter(indexing_eligible=True).exclude(
        editorial_description__regex=r"^\s*$"
    )


def sitemap_batches():
    return [
        {
            "kind": kind,
            "pages": ceil(indexable_records(kind).count() / SITEMAP_BATCH_SIZE),
        }
        for kind in SITEMAP_KINDS
    ]


def sitemap_entries(kind, page):
    if page < 1:
        raise Http404
    offset = (page - 1) * SITEMAP_BATCH_SIZE
    entries = list(
        indexable_records(kind)
        .order_by("id")
        .values("slug", "updated_at")[offset : offset + SITEMAP_BATCH_SIZE]
    )
    if not entries:
        raise Http404
    return entries
