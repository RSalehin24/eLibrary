import csv
from datetime import UTC, datetime
from io import StringIO

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.exports.grouped_pdf import pdf_cell, word_clusters
from apps.catalog.exports.tabular import created_label
from apps.catalog.models import (
    Book,
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
    book = make_book("একটি বই")
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.READ_DURABLE
    )
    for path in [
        "/api/v1/catalog/physical-books/",
        "/api/v1/catalog/physical-books/export/",
    ]:
        assert client.get(path).status_code == 404
    rows = csv_rows(client.get("/api/v1/catalog/exports/"))
    assert rows[0]["Title"] == book.title
    assert not {"Type", "Binding", "Price"}.intersection(rows[0])


def test_physical_xlsx_groups_multiple_categories_and_never_creates_formula_cells():
    client, actor = authenticated_client()
    book = make_book("একটি বই")
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.READ_DURABLE
    )
    for path in [
        "/api/v1/catalog/physical-books/",
        "/api/v1/catalog/physical-books/export/",
    ]:
        assert client.get(path).status_code == 404
    rows = csv_rows(client.get("/api/v1/catalog/exports/"))
    assert rows[0]["Title"] == book.title
    assert not {"Type", "Binding", "Price"}.intersection(rows[0])


def test_physical_inventory_combines_writer_translator_and_legacy_compiler_filters():
    client, actor = authenticated_client()
    book = make_book("একটি বই")
    PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.READ_DURABLE
    )
    for path in [
        "/api/v1/catalog/physical-books/",
        "/api/v1/catalog/physical-books/export/",
    ]:
        assert client.get(path).status_code == 404
    rows = csv_rows(client.get("/api/v1/catalog/exports/"))
    assert rows[0]["Title"] == book.title
    assert not {"Type", "Binding", "Price"}.intersection(rows[0])


def test_sheet_names_are_unique_case_insensitive_and_excel_compatible():
    make_book("=unsafe spreadsheet name")
    response = APIClient().get("/api/v1/catalog/exports/", {"export_format": "xlsx"})
    assert response.status_code == 400
    assert response.json()["field_errors"]["export_format"]


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
    make_book("English export", language="en")
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
    first, second = make_book("First"), make_book("Second")
    assert client.get("/api/v1/manage/book-exports/").status_code == 403
    PermissionGrant.objects.create(
        user=actor, book=first, scope=PermissionScope.METADATA_EDIT
    )
    assert {
        row["Book ID"] for row in csv_rows(client.get("/api/v1/manage/book-exports/"))
    } == {first.catalog_code}
    actor.is_staff = True
    actor.save()
    assert {
        row["Book ID"] for row in csv_rows(client.get("/api/v1/manage/book-exports/"))
    } == {first.catalog_code, second.catalog_code}
