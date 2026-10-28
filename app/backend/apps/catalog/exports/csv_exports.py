from io import StringIO

from apps.catalog.models import ContributorRole

from .common import (
    book_export_filename,
    contributor_names_by_role,
    contributor_names_for_roles,
    csv_response,
    csv_value,
    table_contributor_lines,
)
from .tabular import created_label


def build_books_csv_response(books):
    output = StringIO()
    writer = __import__("csv").writer(output)
    writer.writerow(
        [
            "Book ID",
            "Title",
            "Writer / Translator / Editor / Publisher",
            "Writers",
            "Translators",
            "Editors",
            "Publishers",
            "Categories",
            "Series",
            "Compilation",
            "Publisher",
            "Created At",
            "Language",
            "Edition",
        ]
    )
    for book in books:
        writer.writerow(
            [
                csv_value(book.catalog_code),
                csv_value(book.title),
                csv_value(" | ".join(table_contributor_lines(book))),
                csv_value(
                    ", ".join(contributor_names_by_role(book, ContributorRole.AUTHOR))
                ),
                csv_value(
                    ", ".join(
                        contributor_names_by_role(book, ContributorRole.TRANSLATOR)
                    )
                ),
                csv_value(
                    ", ".join(
                        contributor_names_for_roles(
                            book, ContributorRole.COMPILER, ContributorRole.EDITOR
                        )
                    )
                ),
                csv_value(
                    ", ".join(
                        contributor_names_by_role(book, ContributorRole.PUBLISHER)
                    )
                ),
                csv_value(
                    ", ".join(
                        relation.category.name
                        for relation in book.book_categories.all()
                    )
                ),
                csv_value(
                    ", ".join(
                        relation.series.name for relation in book.book_series.all()
                    )
                ),
                "Yes" if book.is_compilation else "No",
                csv_value(book.publisher),
                csv_value(created_label(book)),
                csv_value(book.language),
                csv_value(book.edition),
            ]
        )
    return csv_response(book_export_filename("catalog", "csv"), output)
