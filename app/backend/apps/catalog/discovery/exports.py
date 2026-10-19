from django.db.models import Q

from apps.access.book_permissions import books_with_scopes
from apps.access.models import PermissionScope
from apps.catalog.discovery.facets import matching_entity_ids
from apps.catalog.discovery.queries import (
    filter_public_books,
    search_public_books,
    with_public_relations,
)
from apps.catalog.discovery.sorting import (
    CatalogSortPagination,
    filter_owned_books,
    with_requested_at,
)
from apps.catalog.models import BookRecordType, Contributor, ContributorRole


def ordered_export_queryset(queryset, parameters):
    if not parameters.get("sort"):
        return queryset.order_by("search_rank", "-created_at", "-id")
    ordering = CatalogSortPagination(parameters["sort"])
    prefix = "-" if ordering.descending else ""
    return ordering.prepared_queryset(queryset).order_by(
        prefix + "catalog_sort_value", prefix + "id"
    )


def physical_book_queryset(actor, parameters):
    queryset = books_with_scopes(actor, [PermissionScope.PHYSICAL_BOOKS_VIEW]).filter(
        record_type=BookRecordType.MANUAL
    )
    queryset = filter_public_books(queryset, {**parameters, "record_type": "manual"})
    queryset = filter_owned_books(queryset, parameters, actor)
    if parameters.get("sort", "").lstrip("-") == "requested_at":
        queryset = with_requested_at(queryset, actor)
    queryset = filter_physical_details(queryset, parameters)
    return ordered_export_queryset(
        with_public_relations(search_public_books(queryset, parameters["q"])),
        parameters,
    )


def filter_physical_details(queryset, parameters):
    queryset = filter_physical_contributors(queryset, parameters)
    if binding := parameters.get("binding"):
        queryset = queryset.filter(manual_binding=binding)
    if language := parameters.get("language"):
        queryset = queryset.filter(manual_language=language)
    if publisher := parameters.get("publisher"):
        queryset = queryset.filter(
            Q(manual_publisher__iexact=publisher)
            | Q(
                book_contributors__role=ContributorRole.PUBLISHER,
                book_contributors__contributor_id__in=matching_entity_ids(
                    Contributor, publisher
                ),
            )
        )
    return queryset.distinct()


def filter_physical_contributors(queryset, parameters):
    for parameter, roles in (
        ("writer", (ContributorRole.AUTHOR,)),
        ("translator", (ContributorRole.TRANSLATOR,)),
        ("editor", (ContributorRole.EDITOR, ContributorRole.COMPILER)),
    ):
        if value := parameters.get(parameter):
            queryset = queryset.filter(
                book_contributors__role__in=roles,
                book_contributors__contributor_id__in=matching_entity_ids(
                    Contributor, value
                ),
            )
    return queryset
