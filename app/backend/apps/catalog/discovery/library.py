from apps.catalog.discovery.personal import annotate_personal_books, personal_feed
from apps.catalog.discovery.queries import (
    PUBLIC_BOOK_FIELDS,
    filter_public_books,
    search_public_books,
    with_public_relations,
)
from apps.catalog.models import Book


def library_books(user):
    return annotate_personal_books(
        Book.objects.filter(user_books__user=user, deleted_at__isnull=True).only(
            *PUBLIC_BOOK_FIELDS,
            "state",
            "review_state",
            "record_type",
        ),
        user,
    )


def library_queryset(user, parameters):
    queryset = annotate_personal_books(
        personal_feed(user, parameters.get("view", "owned")), user
    ).only(*PUBLIC_BOOK_FIELDS, "state", "review_state", "record_type")
    queryset = filter_public_books(queryset, parameters)
    return with_public_relations(search_public_books(queryset, parameters["q"]))
