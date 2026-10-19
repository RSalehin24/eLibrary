from apps.access.models import PermissionScope
from apps.catalog.discovery.queries import (
    PUBLIC_BOOK_FIELDS,
    filter_public_books,
    search_public_books,
    with_public_relations,
)
from apps.catalog.models import CuratedCollection

from .facets import matching_entity_ids
from .sorting import CatalogSortPagination, filter_owned_books, with_requested_at


def metadata_managed_books(user):
    from apps.access.book_permissions import books_with_scopes

    return books_with_scopes(user, [PermissionScope.METADATA_EDIT])


def managed_book_queryset(user, parameters):
    queryset = metadata_managed_books(user).only(
        *PUBLIC_BOOK_FIELDS,
        "state",
        "review_state",
        "record_type",
    )
    if collection := parameters.get("collection"):
        queryset = queryset.filter(
            collection_books__collection_id__in=matching_entity_ids(
                CuratedCollection, collection
            )
        )
    filters = {**parameters, "collection": ""}
    queryset = filter_public_books(queryset, filters)
    queryset = filter_owned_books(queryset, parameters, user)
    if parameters.get("sort", "").lstrip("-") == "requested_at":
        queryset = with_requested_at(queryset, user)
    if parameters.get("sort"):
        pagination = CatalogSortPagination(parameters["sort"])
        prefix = "-" if pagination.descending else ""
        return with_public_relations(
            pagination.prepared_queryset(search_public_books(queryset, parameters["q"]))
        ).order_by(prefix + "catalog_sort_value", prefix + "id")
    return with_public_relations(
        search_public_books(queryset, parameters["q"])
    ).order_by(
        "search_rank",
        "-created_at",
        "-id",
    )
