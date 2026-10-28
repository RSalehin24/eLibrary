from datetime import timedelta

import pytest
from apps.catalog.models import Book, BookContributor, Contributor
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.fixture
def corpus():
    author = Contributor.objects.create(name="বিভূতিভূষণ বন্দ্যোপাধ্যায়")
    reviewed = timezone.now()
    novels = [
        Book.objects.create(title=title, alternative_names=aliases, state="published")
        for title, aliases in [
            ("পথের পাঁচালী", ["Pather Panchali"]),
            ("পথের পাঁচালী: দ্বিতীয় সংস্করণ", []),
            ("অপরাজিত", ["Aparajito"]),
        ]
    ]
    for book in novels:
        BookContributor.objects.create(book=book, contributor=author, role="author")
    Book.objects.create(
        title="পথের পাঁচালী", state="draft", alternative_names=["Hidden Alias"]
    )
    Book.objects.filter(pk=novels[0].pk).update(created_at=reviewed - timedelta(days=1))
    return novels


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("পথের পাঁচালী", [0, 1]),
        ("পথের পাঁচালী বিভূতিভূষণ", [1, 0]),
        ("বিভূতিভূষণ অপরাজিত", [2]),
        ("Pather Panchali", [0]),
        ("  PATHER   panchali  ", [0]),
        ("অপরা\u200dজিত", [2]),
        ("অপরাজিত !!!", [2]),
        ("পথের অজানা", []),
        ("Hidden Alias", []),
    ],
)
def test_representative_bengali_and_reviewed_romanized_intents(
    client, corpus, query, expected
):
    response = client.get("/api/v1/catalog/books/", {"q": query})
    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()["entries"]] == [
        str(corpus[index].pk) for index in expected
    ]


def test_corpus_identifier_and_published_aliases_do_not_require_review(client, corpus):
    book = corpus[0]
    response = client.get("/api/v1/catalog/books/", {"q": book.catalog_code.lower()})
    assert [entry["id"] for entry in response.json()["entries"]] == [str(book.pk)]
    Book.objects.filter(pk=book.pk).update()
    assert client.get("/api/v1/catalog/books/", {"q": "Pather Panchali"}).json()[
        "entries"
    ][0]["id"] == str(book.pk)
