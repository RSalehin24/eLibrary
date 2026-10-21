from typing import ClassVar

from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.catalog.discovery.publication import public_books
from apps.catalog.models import (
    BookCategory,
    BookContributor,
    BookSeries,
    CollectionBook,
)

from .sorting import CatalogSortPagination

DIRECTORY_SORTS = (
    "",
    "name",
    "-name",
    "book_count",
    "-book_count",
    "catalog_code",
    "-catalog_code",
    "created_at",
    "-created_at",
)
ENTITY_RELATIONS: dict[
    str, tuple[type[BookContributor | BookCategory | BookSeries | CollectionBook], str]
] = {
    "contributors": (BookContributor, "contributor_id"),
    "categories": (BookCategory, "category_id"),
    "series": (BookSeries, "series_id"),
    "collections": (CollectionBook, "collection_id"),
}


class DirectorySortPagination(CatalogSortPagination):
    ordering_choices = DIRECTORY_SORTS
    text_fields: ClassVar[dict[str, str]] = {
        "name": "normalized_name",
        "catalog_code": "catalog_code",
    }
    number_fields = ("book_count",)


def with_directory_counts(queryset, kind, parameters):
    model, field = ENTITY_RELATIONS[kind]
    books = public_books()
    if parameters.get("record_type", "all") != "all":
        books = books.filter(record_type=parameters["record_type"])
    role = parameters.get("role") if kind == "contributors" else ""
    links = model.objects.filter(
        Q(role=role) if role else Q(), **{field: OuterRef("pk")}, book_id__in=books
    )
    counts = (
        links.order_by().values(field).annotate(total=Count("book_id", distinct=True))
    )
    return queryset.annotate(
        book_count=Coalesce(
            Subquery(counts.values("total")[:1]), Value(0), output_field=IntegerField()
        )
    ).filter(book_count__gt=0)
