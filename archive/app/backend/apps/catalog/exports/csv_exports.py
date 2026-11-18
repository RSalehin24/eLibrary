from io import StringIO

from apps.catalog.models import BookRecordType, ContributorRole

from .common import book_export_filename, contributor_names_by_role, contributor_names_for_roles, csv_response, csv_value, table_contributor_lines


def build_books_csv_response(books, *, record_type):
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
            "Type",
            "Compilation",
            "Binding",
            "Publisher",
            "Price",
            "Created At",
        ]
    )
    for book in books:
        writer.writerow(
            [
                csv_value(book.catalog_code),
                csv_value(book.title),
                csv_value(" | ".join(table_contributor_lines(book))),
                csv_value(", ".join(contributor_names_by_role(book, ContributorRole.AUTHOR))),
                csv_value(", ".join(contributor_names_by_role(book, ContributorRole.TRANSLATOR))),
                csv_value(", ".join(contributor_names_for_roles(book, ContributorRole.COMPILER, ContributorRole.EDITOR))),
                csv_value(", ".join(contributor_names_by_role(book, ContributorRole.PUBLISHER))),
                csv_value(", ".join(relation.category.name for relation in book.book_categories.all())),
                csv_value(", ".join(relation.series.name for relation in book.book_series.all())),
                "Manual" if book.record_type == BookRecordType.MANUAL else "Digital",
                "Yes" if book.manual_is_compilation else "No",
                csv_value(book.get_manual_binding_display() if book.manual_binding else ""),
                csv_value(book.manual_publisher),
                csv_value(book.manual_price),
                csv_value(book.created_at.isoformat() if book.created_at else ""),
            ]
        )
    return csv_response(book_export_filename("catalog", "csv", record_type=record_type), output)
