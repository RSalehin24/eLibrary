from collections import OrderedDict
from zoneinfo import ZoneInfo

from apps.catalog.models import Book, ContributorRole

from .common import contributor_names_for_roles

HEADERS = (
    "Book ID",
    "Title",
    "Writers",
    "Translators",
    "Editors",
    "Publisher",
    "Categories",
    "Language",
    "Created At",
)
GROUPS = ("", "category", "publisher", "language", "contributor")


def created_label(book):
    return (
        book.created_at.astimezone(ZoneInfo("Asia/Dhaka")).strftime(
            "%d %b %Y, %I:%M %p"
        )
        if book.created_at
        else ""
    )


def group_labels(book, grouping):
    if grouping == "category":
        return [relation.category.name for relation in book.book_categories.all()]
    if grouping == "contributor":
        return contributor_names_for_roles(
            book,
            ContributorRole.AUTHOR,
            ContributorRole.TRANSLATOR,
            ContributorRole.EDITOR,
            ContributorRole.COMPILER,
        )
    return [
        {
            "publisher": book.publisher,
            "language": book.language,
        }.get(grouping, "")
    ]


def grouped_books(books, grouping):
    if not grouping:
        return [("Books", books)]
    groups: OrderedDict[str, list[Book]] = OrderedDict()
    for book in books:
        for label in dict.fromkeys(group_labels(book, grouping) or ["(None)"]):
            groups.setdefault(label or "(None)", []).append(book)
    return list(groups.items()) or [("Books", [])]
