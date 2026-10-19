import csv
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO, StringIO
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.exports.grouped_pdf import pdf_cell, word_clusters
from apps.catalog.exports.tabular import created_label
from apps.catalog.exports.xlsx_exports import sheet_names
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    Category,
    Contributor,
    UserBook,
)
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def make_book(title, **values):
    return Book.objects.create(title=title, state="published", **values)


def csv_rows(response):
    assert response.status_code == 200
    return list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))


def authenticated_client():
    actor = User.objects.create_user(email="export-owner@example.test")
    client = APIClient()
    client.force_authenticate(actor)
    return client, actor


def test_catalog_export_contains_entire_filtered_set_and_excludes_private_books():
    books = [make_book(f"Selected {index}") for index in range(26)]
    hidden = make_book("Selected hidden")
    Book.objects.filter(pk=hidden.pk).update(state="draft")
    quarantined = make_book("Selected quarantine", source_quality_state="quarantined")
    make_book("Other book")
    response = APIClient().get(
        "/api/v1/catalog/exports/",
        {"q": "Selected", "page": 2, "limit": 1, "sort": "title"},
    )
    rows = csv_rows(response)
    assert len(rows) == 26
    assert {row["Book ID"] for row in rows} == {book.catalog_code for book in books}
    assert hidden.catalog_code not in response.content.decode()
    assert quarantined.catalog_code not in response.content.decode()
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("title", ["=SUM(1,1)", "+cmd", "-cmd", "@cmd", "  =cmd"])
def test_csv_formula_prefixes_are_escaped(title):
    book = make_book(title)
    rows = csv_rows(APIClient().get("/api/v1/catalog/exports/"))
    assert rows[0]["Title"] == "'" + book.title


def test_library_export_is_owner_private_and_preserves_filters():
    client, actor = authenticated_client()
    owned = make_book("Owned selected")
    other = make_book("Other selected")
    UserBook.objects.create(user=actor, book=owned)
    stranger = User.objects.create_user(email="export-other@example.test")
    UserBook.objects.create(user=stranger, book=other)
    rows = csv_rows(
        client.get("/api/v1/me/books/export/", {"view": "owned", "q": "selected"})
    )
    assert [row["Title"] for row in rows] == [owned.title]
    assert APIClient().get("/api/v1/me/books/export/").status_code == 403


def test_physical_list_and_export_honor_book_scoped_permissions_and_filters():
    client, actor = authenticated_client()
    allowed = make_book(
        "Physical allowed",
        record_type="manual",
        manual_binding="hard_cover",
        manual_publisher="Publisher",
        manual_price=Decimal("0.00"),
    )
    make_book("Physical denied", record_type="manual", manual_binding="hard_cover")
    make_book("Digital excluded")
    PermissionGrant.objects.create(
        user=actor, book=allowed, scope=PermissionScope.PHYSICAL_BOOKS_VIEW
    )
    parameters = {"binding": "hard_cover", "publisher": "Publisher", "language": "bn"}
    listing = client.get("/api/v1/catalog/physical-books/", parameters)
    assert listing.status_code == 200
    assert [entry["id"] for entry in listing.json()["entries"]] == [str(allowed.pk)]
    rows = csv_rows(client.get("/api/v1/catalog/physical-books/export/", parameters))
    assert [row["Title"] for row in rows] == [allowed.title]
    assert rows[0]["Price"] == "0.00"
    assert rows[0]["Language"] == "bn"
    assert "AM" in rows[0]["Created At"] or "PM" in rows[0]["Created At"]
    assert (
        client.get("/api/v1/catalog/physical-books/", {"binding": "paper_back"}).json()[
            "entries"
        ]
        == []
    )
    PermissionGrant.objects.filter(user=actor).update(is_active=False)
    assert not client.get("/api/v1/catalog/physical-books/").json()["entries"]


def test_physical_xlsx_groups_multiple_categories_and_never_creates_formula_cells():
    client, actor = authenticated_client()
    PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.PHYSICAL_BOOKS_VIEW
    )
    book = make_book(
        "=Formula বাংলাদেশ", record_type="manual", manual_price=Decimal("12.30")
    )
    prefix = "বিভাগ " + "ক" * 30
    categories = [
        Category.objects.create(name=prefix + ending) for ending in [" এক", " দুই"]
    ]
    for category in categories:
        BookCategory.objects.create(book=book, category=category)
    response = client.get(
        "/api/v1/catalog/physical-books/export/",
        {"export_format": "xlsx", "group_by": "category"},
    )
    assert response.status_code == 200
    assert response["Content-Type"].endswith("spreadsheetml.sheet")
    with ZipFile(BytesIO(response.content)) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        names = [
            element.attrib["name"]
            for element in workbook.iter()
            if element.tag.endswith("}sheet")
        ]
        assert names == [prefix[:31], prefix[:27] + " (2)"]
        for index in [1, 2]:
            sheet = ElementTree.fromstring(
                archive.read(f"xl/worksheets/sheet{index}.xml")
            )
            assert not any(element.tag.endswith("}f") for element in sheet.iter())
            text = " ".join(element.text or "" for element in sheet.iter())
            assert "=Formula বাংলাদেশ" in text
            assert "12.30" in text
            assert all(
                element.attrib.get("t") == "inlineStr"
                for element in sheet.iter()
                if element.tag.endswith("}c")
            )


def test_physical_inventory_combines_writer_translator_and_legacy_compiler_filters():
    client, actor = authenticated_client()
    PermissionGrant.objects.create(
        user=actor, scope=PermissionScope.PHYSICAL_BOOKS_VIEW
    )
    selected = make_book("All contributors", record_type="manual")
    excluded = make_book("Wrong contributor roles", record_type="manual")
    contributors = {
        role: Contributor.objects.create(name=name)
        for role, name in [
            ("author", "Writer selected"),
            ("translator", "Translator selected"),
            ("compiler", "Editor selected"),
        ]
    }
    for role, contributor in contributors.items():
        BookContributor.objects.create(
            book=selected, contributor=contributor, role=role
        )
        BookContributor.objects.create(
            book=excluded, contributor=contributor, role="publisher"
        )
    response = client.get(
        "/api/v1/catalog/physical-books/",
        {
            "writer": "Writer selected",
            "translator": "Translator selected",
            "editor": "Editor selected",
        },
    )
    assert [entry["id"] for entry in response.json()["entries"]] == [str(selected.pk)]


def test_sheet_names_are_unique_case_insensitive_and_excel_compatible():
    names = sheet_names(["A" * 40, "a" * 40, "A" * 40, "'", "x/y", "x:y"])
    assert len({name.casefold() for name in names}) == len(names)
    assert all(0 < len(name) <= 31 for name in names)
    assert names[-2:] == ["x_y", "x_y (2)"]


@pytest.mark.parametrize(
    "parameters",
    [{"export_format": "exe"}, {"sort": "password"}, {"record_type": "private"}],
)
def test_catalog_export_rejects_invalid_parameters(parameters):
    assert APIClient().get("/api/v1/catalog/exports/", parameters).status_code == 400


def test_print_export_is_complete_and_html_escaped():
    make_book("<script>alert(1)</script>")
    response = APIClient().get("/api/v1/catalog/exports/", {"export_format": "print"})
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert b"&lt;script&gt;" in response.content and b"<script>" not in response.content
    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]


def test_pdf_export_returns_real_pdf_for_supported_text():
    make_book("English export", manual_language="en")
    response = APIClient().get("/api/v1/catalog/exports/", {"export_format": "pdf"})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_pdf_ascii_cells_keep_latin_glyphs_instead_of_using_bengali_subset_font():
    from reportlab.pdfbase import pdfmetrics

    cell = pdf_cell("Book ID ABC", 22)
    face = pdfmetrics.getFont(cell.style.fontName).face
    assert all(character in face.glyphWidths for character in ["A", "B", "C"])


def test_pdf_word_wrapping_preserves_bengali_conjuncts_and_vowel_marks():
    assert word_clusters("প্রকাশক") == ["প্র", "কা", "শ", "ক"]


def test_export_dates_are_twelve_hour_dhaka_time():
    book = make_book("Date export")
    book.created_at = datetime(2026, 1, 1, 16, 5, tzinfo=UTC)
    assert created_label(book) == "01 Jan 2026, 10:05 PM"


def test_bengali_pdf_refuses_to_silently_lose_text_shaping(monkeypatch):
    make_book("বাংলা বই")
    monkeypatch.setattr(
        "apps.catalog.exports.grouped_pdf.features.check_feature", lambda _: False
    )
    response = APIClient().get("/api/v1/catalog/exports/", {"export_format": "pdf"})
    assert response.status_code == 503
    assert "RAQM" in response.json()["detail"]


def test_managed_export_enforces_exact_metadata_scope():
    client, actor = authenticated_client()
    permitted = make_book("Manage selected")
    other = make_book("Manage forbidden")
    assert client.get("/api/v1/manage/book-exports/").status_code == 403
    PermissionGrant.objects.create(
        user=actor, book=permitted, scope=PermissionScope.METADATA_EDIT
    )
    rows = csv_rows(client.get("/api/v1/manage/book-exports/"))
    assert [row["Title"] for row in rows] == [permitted.title]
    assert other.catalog_code not in {row["Book ID"] for row in rows}
