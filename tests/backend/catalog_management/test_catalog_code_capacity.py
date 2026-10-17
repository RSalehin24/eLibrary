import pytest
from apps.catalog.models import Book, catalog_codes


def test_catalog_sequence_prefers_the_next_number_before_reusing_gaps():
    assert catalog_codes.available_book_sequence({1, 3}) == 4
    assert catalog_codes.available_book_sequence(set()) == 1


def test_catalog_sequence_reuses_a_free_slot_at_the_encoded_limit():
    maximum = catalog_codes.BOOK_SEQUENCE_MASK
    assert catalog_codes.available_book_sequence({1, 2, maximum}) == 3
    assert catalog_codes.available_book_sequence(set(range(2, maximum + 1))) == 1


def test_genuinely_full_catalog_sequence_range_still_fails_explicitly():
    used = set(range(1, catalog_codes.BOOK_SEQUENCE_MASK + 1))
    with pytest.raises(ValueError, match="capacity exceeded"):
        catalog_codes.available_book_sequence(used)


@pytest.mark.django_db
def test_book_creation_can_allocate_a_free_code_after_a_pair_reaches_its_limit(
    monkeypatch,
):
    monkeypatch.setattr(catalog_codes, "BOOK_SEQUENCE_MASK", 3)
    first = Book.objects.create(title="আগের বই")
    second = Book.objects.create(title="দ্বিতীয় বই")
    third = Book.objects.create(title="শেষ সীমার বই")
    Book.objects.filter(pk=first.pk).update(catalog_code=None)
    created = Book.objects.create(title="খালি নম্বরের নতুন বই")
    assert (
        catalog_codes.decode_book_catalog_code(created.catalog_code)["book_sequence"]
        == 1
    )
    assert created.catalog_code not in {second.catalog_code, third.catalog_code}
