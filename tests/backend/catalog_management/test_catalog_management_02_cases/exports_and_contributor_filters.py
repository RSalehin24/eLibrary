import pytest
from apps.accounts.models import User
from apps.catalog.models import Book
from apps.catalog.services import get_or_create_contributor, replace_book_relations


@pytest.mark.django_db
def test_manual_book_listing_supports_optional_pagination_payload(client):
    actor = User.objects.create_superuser(
        email="retired-list@example.test", password="strong-password-123"
    )
    client.force_login(actor)
    response = client.get("/api/catalog/manual-books/?limit=2&page=1")
    assert response.status_code == 404
    assert not Book.objects.exists()


@pytest.mark.django_db
def test_book_csv_export_includes_merged_editor_and_publisher_columns(client):
    user = User.objects.create_user(
        email="export-reader@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="রপ্তানি বই", state="ready")
    replace_book_relations(
        book,
        contributors=[
            {"name": "লেখক রপ্তানি", "role": "author"},
            {"name": "অনুবাদক রপ্তানি", "role": "translator"},
            {"name": "সংকলক রপ্তানি", "role": "compiler"},
            {"name": "সম্পাদক রপ্তানি", "role": "editor"},
            {"name": "প্রকাশক রপ্তানি", "role": "publisher"},
        ],
        category_names=["রপ্তানি বিভাগ"],
        series_names=["রপ্তানি সিরিজ"],
    )
    client.force_login(user)

    response = client.get("/api/catalog/books/export/?format=csv")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    csv_text = response.content.decode("utf-8-sig")
    assert "Book ID,Title,Writer / Translator / Editor / Publisher" in csv_text
    assert "Translator: অনুবাদক রপ্তানি" in csv_text
    assert "সংকলক রপ্তানি" in csv_text
    assert "সম্পাদক রপ্তানি" in csv_text
    assert "Publisher: প্রকাশক রপ্তানি" in csv_text


@pytest.mark.django_db
def test_book_list_can_filter_by_contributor_code_and_role(client):
    user = User.objects.create_user(
        email="contributor-filter@example.com", password="strong-password-123"
    )
    translator = get_or_create_contributor("ফিল্টার অনুবাদক")
    translated_book = Book.objects.create(title="অনূদিত বই", state="ready")
    edited_book = Book.objects.create(title="সম্পাদিত বই", state="ready")
    replace_book_relations(
        translated_book,
        contributors=[
            {"name": translator.name, "role": "translator", "id": translator.pk}
        ],
    )
    replace_book_relations(
        edited_book,
        contributors=[{"name": translator.name, "role": "editor", "id": translator.pk}],
    )
    client.force_login(user)

    response = client.get(
        f"/api/catalog/books/?contributor_code={translator.catalog_code}&contributor_role=translator"
    )

    assert response.status_code == 200
    payload = response.json()
    assert {entry["title"] for entry in payload} == {"অনূদিত বই"}


@pytest.mark.django_db
def test_book_list_editor_filter_includes_legacy_compiler_roles(client):
    user = User.objects.create_user(
        email="editor-filter@example.com", password="strong-password-123"
    )
    contributor = get_or_create_contributor("সমন্বিত সম্পাদক")
    compiler_book = Book.objects.create(title="সংকলিত বই", state="ready")
    editor_book = Book.objects.create(title="সম্পাদিত বই", state="ready")
    replace_book_relations(
        compiler_book,
        contributors=[
            {"name": contributor.name, "role": "compiler", "id": contributor.pk}
        ],
    )
    replace_book_relations(
        editor_book,
        contributors=[
            {"name": contributor.name, "role": "editor", "id": contributor.pk}
        ],
    )
    client.force_login(user)

    response = client.get(
        f"/api/catalog/books/?contributor_code={contributor.catalog_code}&contributor_role=editor"
    )

    assert response.status_code == 200
    payload = response.json()
    assert {entry["title"] for entry in payload} == {"সংকলিত বই", "সম্পাদিত বই"}


@pytest.mark.django_db
def test_book_pdf_and_ticket_exports_return_pdf(client):
    pytest.importorskip("reportlab")
    user = User.objects.create_user(
        email="pdf-reader@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="PDF book", state="ready")
    replace_book_relations(
        book,
        contributors=[{"name": "PDF Author", "role": "author"}],
        category_names=["PDF Category"],
    )
    client.force_login(user)

    pdf_response = client.get("/api/catalog/books/export/?format=pdf")
    ticket_response = client.get("/api/catalog/books/tickets/")

    assert pdf_response.status_code == 200
    assert pdf_response["Content-Type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
    assert ticket_response.status_code == 200
    assert ticket_response["Content-Type"] == "application/pdf"
    assert ticket_response.content.startswith(b"%PDF")
