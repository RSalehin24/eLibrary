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

from apps.catalog.cover_urls import with_cover_asset
from apps.catalog.discovery.entities import public_entities
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
from apps.common.text import normalize_catalog_text

from .facets import matching_entity_ids
from .sorting import filter_owned_books, with_requested_at

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
    return with_cover_asset(queryset).prefetch_related(
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


def filter_contributor_books(queryset, parameters):
    filters = {}
    if parameters["contributor"]:
        filters["book_contributors__contributor_id__in"] = matching_entity_ids(
            Contributor, parameters["contributor"]
        )
    if role := parameters.get("contributor_role"):
        filters["book_contributors__role"] = role
    return queryset.filter(**filters)


def filter_public_books(queryset, parameters):
    queryset = filter_contributor_books(queryset, parameters)
    if parameters.get("record_type", "all") != "all":
        queryset = queryset.filter(record_type=parameters["record_type"])
    for parameter, relation, model in (
        ("category", "book_categories__category_id__in", Category),
        ("series", "book_series__series_id__in", Series),
    ):
        if parameters[parameter]:
            queryset = queryset.filter(
                **{relation: matching_entity_ids(model, parameters[parameter])}
            )
    if collection := parameters.get("collection"):
        queryset = queryset.filter(
            collection_books__collection_id__in=matching_public_collections(collection)
        )
    return queryset.distinct()


def matching_public_collections(value):
    return (
        public_entities("collections")
        .filter(pk__in=matching_entity_ids(CuratedCollection, value))
        .values("pk")
    )


def matching_search_term(normalized):
    contributors = BookContributor.objects.filter(
        Q(contributor__normalized_name__contains=normalized)
        | Q(
            contributor__normalized_aliases__contains=normalized,
        )
    )
    return (
        Q(catalog_code=normalized.upper())
        | Q(normalized_title__contains=normalized)
        | Q(normalized_aliases__contains=normalized)
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


def discovery_queryset(parameters, actor=None):
    queryset = filter_public_books(published_books(), parameters)
    queryset = filter_owned_books(queryset, parameters, actor)
    if parameters.get("sort", "").lstrip("-") == "requested_at":
        queryset = with_requested_at(queryset, actor)
    queryset = search_public_books(queryset, parameters["q"])
    if parameters.get("collection") and not parameters["q"]:
        positions = CollectionBook.objects.filter(
            book_id=OuterRef("pk"),
            collection_id__in=matching_public_collections(parameters["collection"]),
        ).values("position")[:1]
        queryset = queryset.annotate(
            search_rank=Subquery(positions, output_field=IntegerField())
        )
    return with_public_relations(queryset)
