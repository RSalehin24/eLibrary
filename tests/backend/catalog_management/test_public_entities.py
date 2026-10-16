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
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "kind,model,link,field",
    [
        ("contributors", Contributor, BookContributor, "contributor"),
        ("categories", Category, BookCategory, "category"),
        ("series", Series, BookSeries, "series"),
    ],
)
def test_public_entity_requires_a_published_book_and_hides_unreviewed_content(
    client, kind, model, link, field
):
    entity = model.objects.create(
        name="জনপরিচিত নাম", editorial_description="UNREVIEWED"
    )
    book = Book.objects.create(title="খসড়া")
    link.objects.create(book=book, **{field: entity})
    path = f"/api/v1/catalog/entities/{kind}/{entity.slug}/"
    assert client.get(path).status_code == 404
    book.state, book.review_state = "published", "approved"
    book.save()
    response = client.get(path)
    assert response.status_code == 200
    assert "UNREVIEWED" not in response.content.decode()
    assert response.json()["indexable"] is False
    entity.editorial_reviewed_at = timezone.now()
    entity.indexing_eligible = True
    entity.editorial_description = "পর্যালোচিত পরিচিতি"
    old_slug = entity.slug
    entity.name = "নতুন জনপরিচিত নাম"
    entity.save()
    response = client.get(path)
    assert response.json()["slug"] != old_slug
    assert response.json()["editorial_description"] == "পর্যালোচিত পরিচিতি"
    assert response.json()["indexable"] is True
    book.soft_delete()
    assert client.get(path).status_code == 404


def test_unknown_entity_kind_is_not_found(client):
    assert client.get("/api/v1/catalog/entities/private/anything/").status_code == 404
