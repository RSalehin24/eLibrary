from django.db.models import (
    Case,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)

from apps.catalog.discovery.entities import public_entities
from apps.catalog.discovery.publication import public_books
from apps.catalog.models import (
    BookCategory,
    BookContributor,
    BookSeries,
    CollectionBook,
)
from apps.common.text import normalize_catalog_text

PUBLIC_BOOK_FIELDS = (
    "id",
    "title",
    "slug",
    "catalog_code",
    "manual_language",
    "edition",
    "created_at",
)


def published_books():
    return public_books().only(*PUBLIC_BOOK_FIELDS)


def with_public_relations(queryset):
    return queryset.prefetch_related(
        Prefetch(
            "book_contributors",
            queryset=BookContributor.objects.select_related("contributor").only(
                "id",
                "book_id",
                "contributor_id",
                "role",
                "contributor__id",
                "contributor__name",
                "contributor__slug",
            ),
        ),
        Prefetch(
            "book_categories",
            queryset=BookCategory.objects.select_related("category").only(
                "id",
                "book_id",
                "category_id",
                "category__id",
                "category__name",
                "category__slug",
            ),
        ),
        Prefetch(
            "book_series",
            queryset=BookSeries.objects.select_related("series").only(
                "id",
                "book_id",
                "series_id",
                "series__id",
                "series__name",
                "series__slug",
            ),
        ),
    )


def filter_public_books(queryset, parameters):
    for parameter, relation in (
        ("category", "book_categories__category__slug"),
        ("contributor", "book_contributors__contributor__slug"),
        ("series", "book_series__series__slug"),
    ):
        if parameters[parameter]:
            queryset = queryset.filter(**{relation: parameters[parameter]})
    if collection := parameters.get("collection"):
        queryset = queryset.filter(
            collection_books__collection_id__in=public_entities("collections")
            .filter(slug=collection)
            .values("pk")
        )
    return queryset.distinct()


def matching_search_term(normalized):
    contributors = BookContributor.objects.filter(
        Q(contributor__normalized_name__contains=normalized)
        | Q(
            contributor__normalized_aliases__contains=normalized,
            contributor__editorial_reviewed_at__isnull=False,
        )
    )
    return (
        Q(catalog_code=normalized.upper())
        | Q(normalized_title__contains=normalized)
        | Q(
            normalized_aliases__contains=normalized, editorial_reviewed_at__isnull=False
        )
        | Q(pk__in=contributors.values("book_id"))
    )


def search_public_books(queryset, query):
    if not query:
        return queryset.annotate(search_rank=Value(0, output_field=IntegerField()))
    normalized = normalize_catalog_text(query)
    identifier = query.upper()
    terms = Q(catalog_code=identifier)
    textual_match = Q()
    for term in dict.fromkeys(normalized.split()):
        textual_match &= matching_search_term(term)
    queryset = queryset.filter(terms | textual_match)
    return queryset.annotate(
        search_rank=Case(
            When(catalog_code=identifier, then=Value(0)),
            When(normalized_title=normalized, then=Value(1)),
            When(normalized_title__startswith=normalized, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    )


def discovery_queryset(parameters):
    queryset = filter_public_books(published_books(), parameters)
    queryset = search_public_books(queryset, parameters["q"])
    if parameters.get("collection") and not parameters["q"]:
        positions = CollectionBook.objects.filter(
            book_id=OuterRef("pk"), collection__slug=parameters["collection"]
        ).values("position")[:1]
        queryset = queryset.annotate(
            search_rank=Subquery(positions, output_field=IntegerField())
        )
    return with_public_relations(queryset)
