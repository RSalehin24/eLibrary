import unicodedata
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    Category,
    Contributor,
)

pytestmark = pytest.mark.django_db
CATALOG_URL = "/api/v1/catalog/books/"


def published_book(**fields):
    return Book.objects.create(state="published", **fields)


def test_public_feed_exposes_published_undeleted_metadata_without_manual_review(client):
    visible = published_book(
        title="বাংলা গল্প",
        summary="সম্পাদিত পরিচিতি",
        main_content_html="PRIVATE CHAPTER",
        raw_scrape_payload={"secret": "PRIVATE"},
    )
    Book.objects.create(title="খসড়া", state="draft")
    pending = Book.objects.create(title="অপর্যালোচিত", state="published")
    Book.objects.create(title="প্রস্তুত", state="ready")
    withdrawn = published_book(title="প্রত্যাহৃত")
    withdrawn.soft_delete()
    response = client.get(CATALOG_URL)
    assert response.status_code == 200
    assert {entry["id"] for entry in response.json()["entries"]} == {
        str(visible.id),
        str(pending.id),
    }
    assert "PRIVATE" not in response.content.decode()
    assert "summary" not in response.json()["entries"][0]
    assert response["Cache-Control"] == "private, no-store"
    assert response.json()["has_more"] is False
    assert response.json()["next_cursor"] is None


def test_public_detail_contains_visible_metadata_without_content_or_asset_paths(client):
    book = published_book(
        title="জনপদ", summary="মূল সম্পাদকীয় বর্ণনা", book_info_html="PRIVATE INFO"
    )
    author = Contributor.objects.create(name="লেখক")
    BookContributor.objects.create(book=book, contributor=author, role="author")
    response = client.get(f"{CATALOG_URL}{book.slug}/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == book.summary
    assert payload["contributors"][0]["name"] == author.name
    assert set(payload) == {
        "id",
        "title",
        "slug",
        "catalog_code",
        "cover_url",
        "language",
        "edition",
        "contributors",
        "categories",
        "series",
        "summary",
        "publisher",
        "is_compilation",
        "editorial_description",
        "alternative_names",
        "seo_title",
        "seo_description",
        "social_image_url",
        "indexable",
    }
    assert "PRIVATE" not in response.content.decode()


@pytest.mark.parametrize(
    "state,quality",
    [
        ("draft", "unchecked"),
        ("ready", "unchecked"),
        ("published", "quarantined"),
        ("archived", "unchecked"),
    ],
)
def test_nonpublic_detail_returns_404(client, state, quality):
    book = Book.objects.create(
        title="গোপন বই", state=state, source_quality_state=quality
    )
    response = client.get(f"{CATALOG_URL}{book.slug}/")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_cursor_pagination_handles_tied_dates_and_new_insertions(client):
    books = [published_book(title=f"গল্প {index}") for index in range(5)]
    Book.objects.update(created_at=datetime(2026, 1, 1, tzinfo=UTC))
    expected = [
        str(book.id) for book in sorted(books, key=lambda book: book.id, reverse=True)
    ]
    first = client.get(CATALOG_URL, {"limit": 2}).json()
    published_book(title="সদ্য প্রকাশিত")
    second = client.get(
        CATALOG_URL, {"limit": 2, "cursor": first["next_cursor"]}
    ).json()
    third = client.get(
        CATALOG_URL, {"limit": 2, "cursor": second["next_cursor"]}
    ).json()
    received = [
        entry["id"] for page in (first, second, third) for entry in page["entries"]
    ]
    assert received == expected
    assert first["has_more"] is True
    assert third["has_more"] is False
    assert third["next_cursor"] is None


@pytest.mark.parametrize(
    "changes",
    [{"q": "অন্য"}, {"category": "অন্য"}, {"contributor": "অন্য"}, {"series": "অন্য"}],
)
def test_cursor_cannot_be_reused_with_different_filters(client, changes):
    published_book(title="গল্প এক")
    published_book(title="গল্প দুই")
    cursor = client.get(CATALOG_URL, {"q": "গল্প", "limit": 1}).json()["next_cursor"]
    response = client.get(CATALOG_URL, {"q": "গল্প", "cursor": cursor, **changes})
    assert response.status_code == 400
    assert "cursor" in response.json()["field_errors"]


def test_invalid_or_expired_cursor_returns_field_error(client):
    published_book(title="গল্প এক")
    published_book(title="গল্প দুই")
    with patch("django.core.signing.time.time", return_value=1_600_000_000):
        cursor = client.get(CATALOG_URL, {"limit": 1}).json()["next_cursor"]
    with patch("django.core.signing.time.time", return_value=1_600_172_800):
        for token in (cursor, cursor + "tampered", "malformed"):
            response = client.get(CATALOG_URL, {"cursor": token})
            assert response.status_code == 400
            assert response.json()["code"] == "invalid"
            assert "cursor" in response.json()["field_errors"]


@pytest.mark.parametrize(
    "parameters,field",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"limit": "many"}, "limit"),
        ({"q": "!!!"}, "q"),
        ({"q": "ব" * 121}, "q"),
    ],
)
def test_public_parameters_are_validated(client, parameters, field):
    response = client.get(CATALOG_URL, parameters)
    assert response.status_code == 400
    assert field in response.json()["field_errors"]


def test_search_prefers_exact_title_and_identifier(client):
    exact = published_book(title="পথের পাঁচালী")
    published_book(title="পথের পাঁচালী আলোচনা")
    author = Contributor.objects.create(name="পথের পাঁচালী গবেষক")
    related = published_book(title="সাহিত্য পর্যালোচনা")
    BookContributor.objects.create(book=related, contributor=author, role="author")
    result = client.get(CATALOG_URL, {"q": "পথের পাঁচালী"}).json()
    assert result["entries"][0]["id"] == str(exact.id)
    result = client.get(CATALOG_URL, {"q": exact.catalog_code.lower()}).json()
    assert [entry["id"] for entry in result["entries"]] == [str(exact.id)]


def test_search_matches_bengali_combining_characters(client):
    book = published_book(title="বড় গল্প")
    response = client.get(CATALOG_URL, {"q": unicodedata.normalize("NFD", "বড়")})
    assert [entry["id"] for entry in response.json()["entries"]] == [str(book.id)]


def test_list_query_count_is_bounded_and_does_not_load_content(
    client, django_assert_num_queries
):
    category = Category.objects.create(name="গল্প")
    for index in range(30):
        BookCategory.objects.create(
            book=published_book(title=f"গল্প {index}"), category=category
        )
    with django_assert_num_queries(4) as queries:
        response = client.get(CATALOG_URL)
    assert len(response.json()["entries"]) == 24
    assert response.json()["has_more"] is True
    assert (
        '"catalog_book"."main_content_html"' not in queries.captured_queries[0]["sql"]
    )
    assert (
        '"catalog_book"."raw_scrape_payload"' not in queries.captured_queries[0]["sql"]
    )
    with django_assert_num_queries(4):
        response = client.get(CATALOG_URL, {"limit": 100, "category": category.slug})
    assert len(response.json()["entries"]) == 30
