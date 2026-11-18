

@pytest.mark.django_db
def test_manual_book_listing_supports_optional_pagination_payload(client):
    user = User.objects.create_user(
        email="manual-pagination-reader@example.com",
        password="strong-password-123",
    )
    client.force_login(user)

    for index in range(3):
        book = Book.objects.create(
            title=f"Manual Pagination Book {index}",
            state="ready",
            review_state="approved",
            record_type="manual",
        )
        replace_book_relations(
            book,
            contributors=[{"name": f"Manual Pagination Writer {index}", "role": "author"}],
            category_names=[f"Manual Pagination Category {index}"],
        )

    response = client.get("/api/catalog/manual-books/", {"page": 2, "limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["entries"]) == 1
    assert all(entry["record_type"] == "manual" for entry in payload["entries"])
    assert payload["pagination"] == {
        "page": 2,
        "limit": 2,
        "total_count": 3,
        "page_count": 2,
        "has_previous": True,
        "has_next": False,
    }


@pytest.mark.django_db
def test_book_csv_export_includes_merged_editor_and_publisher_columns(client):
    user = User.objects.create_user(email="export-reader@example.com", password="strong-password-123")
    book = Book.objects.create(title="রপ্তানি বই", state="ready", review_state="approved")
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
    user = User.objects.create_user(email="contributor-filter@example.com", password="strong-password-123")
    translator = get_or_create_contributor("ফিল্টার অনুবাদক")
    translated_book = Book.objects.create(title="অনূদিত বই", state="ready", review_state="approved")
    edited_book = Book.objects.create(title="সম্পাদিত বই", state="ready", review_state="approved")
    replace_book_relations(translated_book, contributors=[{"name": translator.name, "role": "translator"}])
    replace_book_relations(edited_book, contributors=[{"name": translator.name, "role": "editor"}])
    client.force_login(user)

    response = client.get(
        f"/api/catalog/books/?record_type=all&contributor_code={translator.catalog_code}&contributor_role=translator"
    )

    assert response.status_code == 200
    payload = response.json()
    assert {entry["title"] for entry in payload} == {"অনূদিত বই"}


@pytest.mark.django_db
def test_book_list_editor_filter_includes_legacy_compiler_roles(client):
    user = User.objects.create_user(email="editor-filter@example.com", password="strong-password-123")
    contributor = get_or_create_contributor("সমন্বিত সম্পাদক")
    compiler_book = Book.objects.create(title="সংকলিত বই", state="ready", review_state="approved")
    editor_book = Book.objects.create(title="সম্পাদিত বই", state="ready", review_state="approved")
    replace_book_relations(compiler_book, contributors=[{"name": contributor.name, "role": "compiler"}])
    replace_book_relations(editor_book, contributors=[{"name": contributor.name, "role": "editor"}])
    client.force_login(user)

    response = client.get(
        f"/api/catalog/books/?record_type=all&contributor_code={contributor.catalog_code}&contributor_role=editor"
    )

    assert response.status_code == 200
    payload = response.json()
    assert {entry["title"] for entry in payload} == {"সংকলিত বই", "সম্পাদিত বই"}


@pytest.mark.django_db
def test_book_pdf_and_ticket_exports_return_pdf(client):
    pytest.importorskip("reportlab")
    user = User.objects.create_user(email="pdf-reader@example.com", password="strong-password-123")
    book = Book.objects.create(title="পিডিএফ বই", state="ready", review_state="approved")
    replace_book_relations(
        book,
        contributors=[{"name": "লেখক পিডিএফ", "role": "author"}],
        category_names=["পিডিএফ বিভাগ"],
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
