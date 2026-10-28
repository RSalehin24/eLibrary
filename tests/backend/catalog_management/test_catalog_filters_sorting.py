from datetime import timedelta
from urllib.parse import urlencode

import pytest
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    Contributor,
    Series,
    UserBook,
)
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def catalog_books():
    return [
        Book.objects.create(title=title, state="published", publisher=publisher)
        for title, publisher in [
            ("Zulu", "Second"),
            ("alpha", "First"),
            ("Alpha", "First"),
            ("Beta", ""),
        ]
    ]


def test_catalog_combines_entities_type_role_and_account_ownership():
    books = catalog_books()
    writer = Contributor.objects.create(name="Writer")
    category = Category.objects.create(name="Category")
    series = Series.objects.create(name="Series")
    for book in books[:2]:
        BookContributor.objects.create(book=book, contributor=writer, role="author")
        BookCategory.objects.create(book=book, category=category)
        BookSeries.objects.create(book=book, series=series)

    books[1].save()
    actor = User.objects.create_user(email="filter-owner@example.test")
    UserBook.objects.create(user=actor, book=books[1])
    client = APIClient()
    values = {
        "contributor": writer.slug,
        "category": category.slug,
        "series": series.slug,
        "contributor_role": "author",
        "ownership": "mine",
    }
    assert client.get("/api/v1/catalog/books/", values).json()["entries"] == []
    client.force_authenticate(actor)
    result = client.get("/api/v1/catalog/books/", values)
    assert result.status_code == 200
    assert [entry["id"] for entry in result.json()["entries"]] == [str(books[1].pk)]
    assert (
        client.get(
            "/api/v1/catalog/books/", {**values, "contributor_role": "translator"}
        ).json()["entries"]
        == []
    )
    assert (
        client.get(
            "/api/v1/catalog/books/", {**values, "record_type": "digital"}
        ).status_code
        == 400
    )
    assert result["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize(
    "ordering",
    [
        "title",
        "-title",
        "created_at",
        "-created_at",
        "catalog_code",
        "-catalog_code",
        "publisher",
        "-publisher",
    ],
)
def test_catalog_sort_cursor_has_stable_ties_and_no_skipped_records(ordering):

    books = catalog_books()
    client = APIClient()
    parameters = {"sort": ordering, "limit": 2}
    first = client.get("/api/v1/catalog/books/", parameters)
    assert first.status_code == 200
    assert first.json()["has_more"]
    second = client.get(
        "/api/v1/catalog/books/", {**parameters, "cursor": first.json()["next_cursor"]}
    )
    assert second.status_code == 200
    identifiers = [
        entry["id"] for page in [first, second] for entry in page.json()["entries"]
    ]
    field = {"title": "normalized_title"}.get(
        ordering.lstrip("-"), ordering.lstrip("-")
    )
    expected = sorted(
        books,
        key=lambda book: (getattr(book, field), book.pk),
        reverse=ordering.startswith("-"),
    )
    assert identifiers == [str(book.pk) for book in expected]
    assert len(set(identifiers)) == 4 and not second.json()["has_more"]
    wrong = client.get(
        "/api/v1/catalog/books/",
        {
            "sort": "-title" if ordering != "-title" else "title",
            "cursor": first.json()["next_cursor"],
        },
    )
    assert wrong.status_code == 400


def test_personal_library_restores_added_date_sort_and_binds_cursor_to_the_account():
    books = catalog_books()
    actor = User.objects.create_user(email="added-sort@example.test")
    other = User.objects.create_user(email="other-added-sort@example.test")
    for index, book in enumerate(books):
        owned = UserBook.objects.create(user=actor, book=book)
        UserBook.objects.filter(pk=owned.pk).update(
            created_at=timezone.now() - timedelta(days=index)
        )
        UserBook.objects.create(user=other, book=book)
    client = APIClient()
    client.force_authenticate(actor)
    query = {"sort": "-requested_at", "ownership": "mine", "limit": 2}
    first = client.get("/api/v1/me/books/", query)
    assert [entry["id"] for entry in first.json()["entries"]] == [
        str(book.pk) for book in books[:2]
    ]
    following = client.get(
        "/api/v1/me/books/", {**query, "cursor": first.json()["next_cursor"]}
    )
    assert [entry["id"] for entry in following.json()["entries"]] == [
        str(book.pk) for book in books[2:]
    ]
    client.force_authenticate(other)
    assert (
        client.get(
            "/api/v1/me/books/", {**query, "cursor": first.json()["next_cursor"]}
        ).status_code
        == 400
    )


def test_catalog_rejects_unknown_sort_and_filter_types():
    client = APIClient()
    for values in [
        {"sort": "raw_scrape_payload"},
        {"ownership": "other-users"},
        {"record_type": "hidden"},
    ]:
        assert (
            client.get("/api/v1/catalog/books/?" + urlencode(values)).status_code == 400
        )


def test_public_catalog_personal_sort_cursor_cannot_cross_accounts():
    books = catalog_books()
    actor = User.objects.create_user(email="public-sort-owner@example.test")
    other = User.objects.create_user(email="public-sort-other@example.test")
    for book in books:
        UserBook.objects.create(user=actor, book=book)
    client = APIClient()
    client.force_authenticate(actor)
    parameters = {"sort": "-requested_at", "limit": 2}
    first = client.get("/api/v1/catalog/books/", parameters)
    assert first.status_code == 200 and first.json()["next_cursor"]
    client.force_authenticate(other)
    response = client.get(
        "/api/v1/catalog/books/",
        {**parameters, "cursor": first.json()["next_cursor"]},
    )
    assert response.status_code == 400


def test_entity_filters_accept_names_without_broadening_exact_profile_links():
    books = catalog_books()
    writer = Contributor.objects.create(name="Writer")
    other = Contributor.objects.create(name="Writer Two")
    BookContributor.objects.create(book=books[0], contributor=writer, role="author")
    BookContributor.objects.create(book=books[1], contributor=other, role="author")
    client = APIClient()
    for value in [writer.slug, writer.name]:
        assert [
            entry["id"]
            for entry in client.get(
                "/api/v1/catalog/books/", {"contributor": value}
            ).json()["entries"]
        ] == [str(books[0].pk)]
    matches = client.get("/api/v1/catalog/books/", {"contributor": "WRIT"}).json()[
        "entries"
    ]
    assert {entry["id"] for entry in matches} == {str(book.pk) for book in books[:2]}
    assert not client.get("/api/v1/catalog/books/", {"contributor": "---"}).json()[
        "entries"
    ]
