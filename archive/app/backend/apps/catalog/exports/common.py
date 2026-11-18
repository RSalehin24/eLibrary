import csv
from html import escape
from io import BytesIO, StringIO
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse

from apps.catalog.models import BookRecordType, ContributorRole
from apps.catalog.services import normalize_book_contributors


COMMON_PDF_FONT_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/NotoSansBengali-Regular.ttf",
    "/Library/Fonts/NotoSans-Regular.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/NotoSansBengali-Regular.ttf",
    "/System/Library/Fonts/Supplemental/NotoSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def html_lines(values):
    return "<br/>".join(escape(value) for value in values if value)


def normalized_book_contributors_for_export(book):
    return normalize_book_contributors([{"name": relation.contributor.name, "role": relation.role} for relation in book.book_contributors.all()])


def contributor_names_by_role(book, role):
    return [entry["name"] for entry in normalized_book_contributors_for_export(book) if entry["role"] == role]


def contributor_names_for_roles(book, *roles):
    role_set = set(roles)
    return [
        entry["name"]
        for entry in normalized_book_contributors_for_export(book)
        if entry["role"] in role_set
    ]


def table_contributor_lines(book):
    authors = contributor_names_by_role(book, ContributorRole.AUTHOR)
    translators = contributor_names_by_role(book, ContributorRole.TRANSLATOR)
    editors = contributor_names_for_roles(book, ContributorRole.COMPILER, ContributorRole.EDITOR)
    publishers = contributor_names_by_role(book, ContributorRole.PUBLISHER)
    lines = []
    if authors:
        lines.append(", ".join(authors))
    if translators:
        lines.append(f"Translator: {', '.join(translators)}")
    if editors:
        lines.append(f"Editor: {', '.join(editors)}")
    if publishers:
        lines.append(f"Publisher: {', '.join(publishers)}")
    return lines or ["Contributor unavailable"]


def identity_ticket_contributor_line(book):
    parts = []
    authors = contributor_names_by_role(book, ContributorRole.AUTHOR)
    translators = contributor_names_by_role(book, ContributorRole.TRANSLATOR)
    editors = contributor_names_for_roles(book, ContributorRole.COMPILER, ContributorRole.EDITOR)
    publishers = contributor_names_by_role(book, ContributorRole.PUBLISHER)
    if authors:
        parts.append(", ".join(authors))
    if translators:
        parts.append(f"Translator: {', '.join(translators)}")
    if editors:
        parts.append(f"Editor: {', '.join(editors)}")
    if publishers:
        parts.append(f"Publisher: {', '.join(publishers)}")
    return " | ".join(parts) or "Contributor unavailable"


def csv_value(value):
    return "" if value is None else str(value)


def book_export_filename(prefix, extension, *, record_type):
    suffix = "manual" if record_type == BookRecordType.MANUAL else "books"
    return f"{prefix}-{suffix}.{extension}"


def resolve_pdf_font():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:
        raise RuntimeError("PDF export requires reportlab to be installed.") from exc

    for index, candidate in enumerate([settings.CATALOG_EXPORT_FONT_PATH, *COMMON_PDF_FONT_PATHS]):
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        font_name = f"CatalogExportFont{index}"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(path)))
        return font_name
    return "Helvetica"


def csv_response(filename, output):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    response.write(output.getvalue())
    return response


def pdf_response(filename, payload):
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
