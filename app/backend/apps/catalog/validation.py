from rest_framework.exceptions import ValidationError

RETIRED_BOOK_FILTERS = frozenset(
    {
        "record_type",
        "book_type",
        "review_state",
        "binding",
        "created_after",
        "created_before",
        "requested_after",
        "requested_before",
        "added_after",
        "added_before",
    }
)


def reject_retired_book_filters(parameters):
    errors = {
        key: "This book filter is no longer supported."
        for key in RETIRED_BOOK_FILTERS.intersection(parameters)
    }
    if errors:
        raise ValidationError(errors)
