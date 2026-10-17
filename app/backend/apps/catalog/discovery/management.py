from apps.access.models import PermissionScope
from apps.catalog.discovery.queries import (
    PUBLIC_BOOK_FIELDS,
    filter_public_books,
    search_public_books,
    with_public_relations,
)


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
        queryset = queryset.filter(collection_books__collection__slug=collection)
    filters = {**parameters, "collection": ""}
    queryset = filter_public_books(queryset, filters)
    return with_public_relations(
        search_public_books(queryset, parameters["q"])
    ).order_by(
        "search_rank",
        "-created_at",
        "-id",
    )
