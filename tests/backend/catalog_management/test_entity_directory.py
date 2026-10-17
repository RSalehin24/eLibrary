import pytest
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    Contributor,
    Series,
)

pytestmark = pytest.mark.django_db
DIRECTORY = "/api/v1/catalog/entities/"


@pytest.mark.parametrize(
    "relation",
    [
        ("contributors", Contributor, BookContributor, "contributor"),
        ("categories", Category, BookCategory, "category"),
        ("series", Series, BookSeries, "series"),
    ],
)
def test_directory_lists_published_relationships_and_hides_draft_names(
    client, relation
):
    kind, model, link, field = relation
    public = model.objects.create(name="প্রকাশিত বইয়ের পরিচয়")
    private = model.objects.create(name="গোপন খসড়ার পরিচয়")
    book = Book.objects.create(title="প্রকাশিত বই", state="published")
    draft = Book.objects.create(title="গোপন খসড়া")
    link.objects.create(book=book, **{field: public})
    link.objects.create(book=draft, **{field: private})
    response = client.get(f"{DIRECTORY}{kind}/")
    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()["entries"]] == [str(public.pk)]
    assert private.name not in response.content.decode()
    assert client.get(f"{DIRECTORY}{kind}/", {"q": public.name}).json()["entries"]
    assert not client.get(f"{DIRECTORY}{kind}/", {"q": private.name}).json()["entries"]


def test_directory_role_must_belong_to_the_same_public_book(client):
    writer = Contributor.objects.create(name="দুই ভূমিকায় লেখক")
    published = Book.objects.create(title="প্রকাশিত অনুবাদ", state="published")
    private = Book.objects.create(title="গোপন মৌলিক বই")
    BookContributor.objects.create(
        book=published, contributor=writer, role="translator"
    )
    BookContributor.objects.create(book=private, contributor=writer, role="author")
    path = f"{DIRECTORY}contributors/"
    assert client.get(path, {"role": "author"}).json()["entries"] == []
    assert [
        entry["id"]
        for entry in client.get(path, {"role": "translator"}).json()["entries"]
    ] == [str(writer.pk)]
    books = client.get(
        "/api/v1/catalog/books/",
        {"contributor": writer.slug, "contributor_role": "author"},
    )
    assert books.json()["entries"] == []


def test_entity_directory_cursor_is_bound_to_kind_and_role(client):
    book = Book.objects.create(title="একাধিক লেখক", state="published")
    for name in ("প্রথম লেখক", "দ্বিতীয় লেখক"):
        contributor = Contributor.objects.create(name=name)
        BookContributor.objects.create(
            book=book, contributor=contributor, role="author"
        )
    first = client.get(
        f"{DIRECTORY}contributors/", {"limit": 1, "role": "author"}
    ).json()
    assert first["has_more"] and first["next_cursor"]
    valid = client.get(
        f"{DIRECTORY}contributors/", {"cursor": first["next_cursor"], "role": "author"}
    )
    assert valid.status_code == 200 and len(valid.json()["entries"]) == 1
    for kind, role in (("contributors", "translator"), ("categories", "")):
        response = client.get(
            f"{DIRECTORY}{kind}/", {"cursor": first["next_cursor"], "role": role}
        )
        assert response.status_code == 400
        assert "cursor" in response.json()["field_errors"]


@pytest.mark.parametrize(
    "route",
    ["contributors/?role=invalid", "categories/?role=author", "series/?limit=101"],
)
def test_entity_directory_validates_filter_input(client, route):
    assert client.get(f"{DIRECTORY}{route}").status_code == 400


def test_unknown_directory_kind_returns_not_found(client):
    assert client.get(f"{DIRECTORY}private/").status_code == 404
