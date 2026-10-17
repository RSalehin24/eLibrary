import unicodedata

import pytest
from apps.catalog.models import Book, BookContributor, Category, Contributor, Series
from apps.catalog.models.editorial import validate_social_image
from django.core.exceptions import ValidationError
from django.utils import timezone

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "model,field",
    [(Book, "title"), (Contributor, "name"), (Category, "name"), (Series, "name")],
)
def test_renaming_preserves_and_reserves_previous_slug(model, field):
    entity = model.objects.create(**{field: "আগের নাম"})
    previous_slug = entity.slug
    setattr(entity, field, "নতুন নাম")
    entity.save()
    assert list(entity.slug_history.values_list("slug", flat=True)) == [previous_slug]
    replacement = model.objects.create(**{field: "আগের নাম"})
    assert replacement.slug != previous_slug
    setattr(replacement, field, "তৃতীয় নাম")
    replacement.save()
    setattr(entity, field, "আগের নাম")
    entity.save()
    assert entity.slug == previous_slug


def test_partial_save_does_not_record_a_slug_that_was_not_persisted():
    book = Book.objects.create(title="আগের নাম")
    previous_slug = book.slug
    book.title = "নতুন নাম"
    book.save(update_fields=["title", "updated_at"])
    book.refresh_from_db()
    assert book.slug == previous_slug
    assert not book.slug_history.exists()


def test_duplicate_long_titles_keep_slugs_within_database_limit():
    first = Book.objects.create(title="ব" * 255)
    second = Book.objects.create(title="ব" * 255)
    assert first.slug != second.slug
    assert len(first.slug) == len(second.slug) == 255


@pytest.mark.parametrize(
    "aliases", ["alias", [None], ["!!!"], [""], ["a"] * 21, ["a" * 256]]
)
def test_invalid_aliases_are_rejected_before_writing(aliases):
    with pytest.raises(ValidationError):
        Book.objects.create(title="বই", alternative_names=aliases)
    assert not Book.objects.exists()


def test_alias_normalization_survives_partial_save():
    book = Book.objects.create(title="বই")
    book.alternative_names = [
        "Pather Panchali",
        "PATHER PANCHALI",
        unicodedata.normalize("NFD", "বড় গল্প"),
    ]
    book.save(update_fields=["alternative_names", "updated_at"])
    book.refresh_from_db()
    assert book.normalized_aliases == "pather panchali\nবড় গল্প"


def test_published_book_aliases_are_searchable_without_review(client):
    book = Book.objects.create(
        title="পথের পাঁচালী",
        state="published",
        review_state="approved",
        alternative_names=["Pather Panchali"],
    )
    assert client.get("/api/v1/catalog/books/?q=Pather").json()["entries"][0][
        "id"
    ] == str(book.pk)
    book.editorial_reviewed_at = timezone.now()
    book.save()
    assert client.get("/api/v1/catalog/books/?q=Pather").json()["entries"][0][
        "id"
    ] == str(book.id)


def test_reviewed_contributor_aliases_match_linked_books(client):
    author = Contributor.objects.create(
        name="রবীন্দ্রনাথ ঠাকুর",
        alternative_names=["Rabindranath Tagore"],
        editorial_reviewed_at=timezone.now(),
    )
    book = Book.objects.create(
        title="গীতাঞ্জলি", state="published", review_state="approved"
    )
    BookContributor.objects.create(book=book, contributor=author)
    assert client.get("/api/v1/catalog/books/?q=Tagore").json()["entries"][0][
        "id"
    ] == str(book.id)


def test_indexing_requires_eligibility_and_substantive_description():
    book = Book(
        title="বই", indexing_eligible=True, editorial_description="সম্পাদিত পরিচিতি"
    )
    assert book.is_indexable is True
    book.editorial_reviewed_at = timezone.now()
    assert book.is_indexable is True
    book.editorial_description = "   "
    assert book.is_indexable is False


@pytest.mark.parametrize(
    "url",
    [
        "http://library.test/a.png",
        "https://user:secret@library.test/a.png",
        "file:///a.png",
    ],
)
def test_social_images_reject_insecure_or_credentialed_urls(url):
    with pytest.raises(ValidationError):
        validate_social_image(url)
