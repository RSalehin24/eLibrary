from django.http import Http404

from apps.catalog.discovery.publication import public_books
from apps.catalog.models import (
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    CollectionBook,
    Contributor,
    CuratedCollection,
    Series,
)
from apps.catalog.serializers.editorial import EDITORIAL_DETAIL_FIELDS


def public_entities(kind):
    if kind == "contributors":
        return related_public_entities(Contributor, BookContributor, "contributor_id")
    if kind == "categories":
        return related_public_entities(Category, BookCategory, "category_id")
    if kind == "series":
        return related_public_entities(Series, BookSeries, "series_id")
    if kind == "collections":
        return (
            related_public_entities(CuratedCollection, CollectionBook, "collection_id")
            .filter(state="published", editorial_reviewed_at__isnull=False)
            .exclude(editorial_description__regex=r"^\s*$")
        )
    raise Http404


def related_public_entities(model, link_model, field):
    links = link_model.objects.filter(book_id__in=public_books().values("pk"))
    return model.objects.filter(pk__in=links.values(field)).only(
        "id", "name", "slug", "created_at", "updated_at", *EDITORIAL_DETAIL_FIELDS
    )
