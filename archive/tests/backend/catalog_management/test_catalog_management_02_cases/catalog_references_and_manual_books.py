import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.utils.text import slugify

from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookContributor,
    BookSource,
    CATALOG_CODE_LENGTH,
    Category,
    Contributor,
    derive_category_catalog_code_from_book_code,
    derive_writer_catalog_code_from_book_code,
    GeneratedAsset,
    GeneratedAssetType,
    MetadataReview,
    MetadataVersion,
    Series,
)
from apps.catalog.services import get_or_create_category, get_or_create_contributor, get_or_create_series, replace_book_relations
from apps.ingestion.models import BookSubmission, DuplicateReview, ProcessingJob


@pytest.mark.django_db
def test_catalog_codes_are_assigned_and_book_code_encodes_category_and_writer():
    category = get_or_create_category("রহস্য")
    writer = get_or_create_contributor("লেখক কোড")
    book = Book.objects.create(title="কোড বই", state="ready", review_state="approved")

    replace_book_relations(
        book,
        contributors=[{"name": writer.name, "role": "author"}],
        category_names=[category.name],
    )

    category.refresh_from_db()
    writer.refresh_from_db()
    book.refresh_from_db()

    assert len(category.catalog_code) == CATALOG_CODE_LENGTH
    assert len(writer.catalog_code) == CATALOG_CODE_LENGTH
    assert len(book.catalog_code) == CATALOG_CODE_LENGTH
    assert category.catalog_code != writer.catalog_code
    assert book.catalog_code not in {category.catalog_code, writer.catalog_code}
    assert derive_category_catalog_code_from_book_code(book.catalog_code) == category.catalog_code
    assert derive_writer_catalog_code_from_book_code(book.catalog_code) == writer.catalog_code


@pytest.mark.django_db
def test_category_and_contributor_listing_endpoints_return_codes_and_counts(client):
    user = User.objects.create_user(email="listing-reader@example.com", password="strong-password-123")
    category = get_or_create_category("তালিকা বিভাগ")
    series = get_or_create_series("তালিকা সিরিজ")
    writer = get_or_create_contributor("তালিকা লেখক")
    translator = get_or_create_contributor("তালিকা অনুবাদক")
    compiler = get_or_create_contributor("তালিকা সংকলক")
    editor = get_or_create_contributor("তালিকা সম্পাদক")
    publisher = get_or_create_contributor("তালিকা প্রকাশক")
    book = Book.objects.create(title="তালিকা বই", state="ready", review_state="approved")
    replace_book_relations(
        book,
        contributors=[
            {"name": writer.name, "role": "author"},
            {"name": translator.name, "role": "translator"},
            {"name": compiler.name, "role": "compiler"},
            {"name": editor.name, "role": "editor"},
            {"name": publisher.name, "role": "publisher"},
        ],
        series_names=[series.name],
        category_names=[category.name],
    )
    Contributor.objects.filter(pk=translator.pk).update(name="তালিকা অনুবাদক)")
    translator.name = "তালিকা অনুবাদক)"
    invalid_translator = Contributor.objects.create(name="and elaborate purports")
    BookContributor.objects.create(
        book=book,
        contributor=invalid_translator,
        role="translator",
        sort_order=99,
    )
    client.force_login(user)

    category_response = client.get("/api/catalog/categories/")
    series_response = client.get("/api/catalog/series/")
    writer_response = client.get("/api/catalog/writers/")
    translator_response = client.get("/api/catalog/translators/")
    compiler_response = client.get("/api/catalog/compilers/")
    editor_response = client.get("/api/catalog/editors/")
    publisher_response = client.get("/api/catalog/publishers/")

    assert category_response.status_code == 200
    assert series_response.status_code == 200
    assert writer_response.status_code == 200
    assert translator_response.status_code == 200
    assert compiler_response.status_code == 200
    assert editor_response.status_code == 200
    assert publisher_response.status_code == 200
    assert category_response.json()[0]["catalog_code"] == category.catalog_code
    assert category_response.json()[0]["book_count"] == 1
    assert series_response.json()[0]["name"] == series.name
    assert series_response.json()[0]["book_count"] == 1
    assert writer_response.json()[0]["catalog_code"] == writer.catalog_code
    assert writer_response.json()[0]["book_count"] == 1
    assert translator_response.json()[0]["catalog_code"] == translator.catalog_code
    assert translator_response.json()[0]["name"] == "তালিকা অনুবাদক"
    assert translator_response.json()[0]["book_count"] == 1
    assert "and elaborate purports" not in {
        entry["name"] for entry in translator_response.json()
    }
    assert compiler_response.json()[0]["catalog_code"] == compiler.catalog_code
    assert compiler_response.json()[0]["book_count"] == 1
    assert {entry["catalog_code"] for entry in editor_response.json()} == {
        compiler.catalog_code,
        editor.catalog_code,
    }
    assert all(entry["book_count"] == 1 for entry in editor_response.json())
    assert publisher_response.json()[0]["catalog_code"] == publisher.catalog_code
    assert publisher_response.json()[0]["book_count"] == 1


@pytest.mark.django_db
def test_reference_listing_search_supports_normalized_bangla_queries(client):
    user = User.objects.create_user(email="reference-search-reader@example.com", password="strong-password-123")
    writer = get_or_create_contributor("ড. মুহম্মদ শহীদুল্লাহ")
    series = get_or_create_series("অ-আ সিরিজ")
    category = get_or_create_category("ভাষা-বিজ্ঞান")
    book = Book.objects.create(title="বাংলা ভাষার বই", state="ready", review_state="approved")
    replace_book_relations(
        book,
        contributors=[{"name": writer.name, "role": "author"}],
        series_names=[series.name],
        category_names=[category.name],
    )
    client.force_login(user)

    writer_response = client.get("/api/catalog/writers/", {"record_type": "all", "q": "ড মুহম্মদ শহীদুল্লাহ"})
    series_response = client.get("/api/catalog/series/", {"record_type": "all", "q": "অ আ সিরিজ"})
    category_response = client.get("/api/catalog/categories/", {"record_type": "all", "q": "ভাষা বিজ্ঞান"})

    assert writer_response.status_code == 200
    assert [entry["name"] for entry in writer_response.json()] == [writer.name]
    assert series_response.status_code == 200
    assert [entry["name"] for entry in series_response.json()] == [series.name]
    assert category_response.status_code == 200
    assert [entry["name"] for entry in category_response.json()] == [category.name]


@pytest.mark.django_db
def test_reference_listing_supports_optional_pagination_payload(client):
    user = User.objects.create_user(
        email="reference-pagination-reader@example.com",
        password="strong-password-123",
    )
    client.force_login(user)

    for index in range(3):
        category = get_or_create_category(f"Pagination Category {index}")
        book = Book.objects.create(
            title=f"Pagination Category Book {index}",
            state="ready",
            review_state="approved",
        )
        replace_book_relations(book, category_names=[category.name])

    response = client.get("/api/catalog/categories/", {"page": 2, "limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["entries"]) == 1
    assert payload["pagination"] == {
        "page": 2,
        "limit": 2,
        "total_count": 3,
        "page_count": 2,
        "has_previous": True,
        "has_next": False,
    }


@pytest.mark.django_db
def test_manual_book_creation_uses_manual_listing_and_stays_hidden_from_default_book_page(client):
    user = User.objects.create_user(email="manual-reader@example.com", password="strong-password-123")
    client.force_login(user)

    response = client.post(
        "/api/catalog/manual-books/",
        data=json.dumps(
            {
                "title": "ম্যানুয়াল বই",
                "summary": "শারীরিক কপি",
                "writers": ["ম্যানুয়াল লেখক"],
                "translators": ["ম্যানুয়াল অনুবাদক"],
                "compilers": ["ম্যানুয়াল সংকলক"],
                "editors": ["ম্যানুয়াল সম্পাদক"],
                "categories": ["ম্যানুয়াল বিভাগ"],
                "series": ["শেলফ ১"],
                "is_compilation": True,
                "binding": "paper_back",
                "publisher": "প্রকাশনা ঘর",
                "price": "350.00",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["record_type"] == "manual"
    assert len(payload["catalog_code"]) == CATALOG_CODE_LENGTH
    assert payload["translators"] == ["ম্যানুয়াল অনুবাদক"]
    assert payload["compilers"] == []
    assert payload["editors"] == ["ম্যানুয়াল সংকলক", "ম্যানুয়াল সম্পাদক"]
    assert payload["is_compilation"] is True
    assert payload["binding"] == "Paper Back"
    assert payload["publisher"] == "প্রকাশনা ঘর"
    assert payload["price"] == "350.00"

    manual_book = Book.objects.get(pk=payload["id"])
    manual_writer_relation = (
        manual_book.book_contributors.filter(role="author")
        .select_related("contributor")
        .first()
    )
    manual_category_relation = manual_book.book_categories.select_related("category").first()
    manual_publisher_relation = (
        manual_book.book_contributors.filter(role="publisher")
        .select_related("contributor")
        .first()
    )
    assert manual_writer_relation is not None
    assert manual_category_relation is not None
    assert manual_publisher_relation is not None
    assert derive_writer_catalog_code_from_book_code(payload["catalog_code"]) == manual_writer_relation.contributor.catalog_code
    assert derive_category_catalog_code_from_book_code(payload["catalog_code"]) == manual_category_relation.category.catalog_code

    manual_response = client.get("/api/catalog/manual-books/")
    default_book_page = client.get("/api/catalog/books/")
    all_books_response = client.get("/api/catalog/books/?record_type=all")

    assert manual_response.status_code == 200
    assert default_book_page.status_code == 200
    assert all(entry["record_type"] == "manual" for entry in manual_response.json())
    assert payload["id"] in {entry["id"] for entry in manual_response.json()}
    assert payload["id"] not in {entry["id"] for entry in default_book_page.json()}
    assert payload["id"] in {entry["id"] for entry in all_books_response.json()}
