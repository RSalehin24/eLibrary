from collections import OrderedDict
from zoneinfo import ZoneInfo

from apps.catalog.models import Book, ContributorRole

from .common import contributor_names_by_role, contributor_names_for_roles

HEADERS = (
    "Book ID",
    "Title",
    "Writers",
    "Translators",
    "Editors",
    "Publisher",
    "Categories",
    "Binding",
    "Language",
    "Price",
    "Created At",
)
GROUPS = ("", "category", "publisher", "binding", "language", "contributor")


def created_label(book):
    return (
        book.created_at.astimezone(ZoneInfo("Asia/Dhaka")).strftime(
            "%d %b %Y, %I:%M %p"
        )
        if book.created_at
        else ""
    )


def physical_book_row(book):
    return (
        book.catalog_code or "",
        book.title,
        ", ".join(contributor_names_by_role(book, ContributorRole.AUTHOR)),
        ", ".join(contributor_names_by_role(book, ContributorRole.TRANSLATOR)),
        ", ".join(
            contributor_names_for_roles(
                book, ContributorRole.EDITOR, ContributorRole.COMPILER
            )
        ),
        book.manual_publisher,
        ", ".join(relation.category.name for relation in book.book_categories.all()),
        book.get_manual_binding_display() if book.manual_binding else "",
        {"bn": "Bengali", "en": "English"}.get(
            book.manual_language, book.manual_language
        ),
        str(book.manual_price) if book.manual_price is not None else "",
        created_label(book),
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
            "publisher": book.manual_publisher,
            "binding": book.get_manual_binding_display() if book.manual_binding else "",
            "language": book.manual_language,
        }.get(grouping, "")
    ]


def grouped_books(books, grouping):
    if not grouping:
        return [("Physical Books", books)]
    groups: OrderedDict[str, list[Book]] = OrderedDict()
    for book in books:
        for label in dict.fromkeys(group_labels(book, grouping) or ["(None)"]):
            groups.setdefault(label or "(None)", []).append(book)
    return list(groups.items()) or [("Physical Books", [])]
