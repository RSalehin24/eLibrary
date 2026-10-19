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


@pytest.mark.django_db
def test_unassigned_books_keep_existing_codes_and_continue_after_legacy_pair_limit(
    monkeypatch,
):
    monkeypatch.setattr(catalog_codes, "BOOK_SEQUENCE_MASK", 3)
    books = [Book.objects.create(title=f"বই {number}") for number in range(3)]
    original_codes = [book.catalog_code for book in books]
    overflow = [Book.objects.create(title=f"নতুন বই {number}") for number in range(2)]
    assert [
        catalog_codes.decode_book_catalog_code(book.catalog_code)["book_sequence"]
        for book in overflow
    ] == [4, 5]
    for book in overflow:
        assert len(book.catalog_code) == catalog_codes.CATALOG_CODE_LENGTH
        assert catalog_codes.is_book_catalog_code(book.catalog_code)
        assert (
            catalog_codes.decode_book_catalog_code(book.catalog_code)["writer_sequence"]
            == 0
        )
        assert (
            catalog_codes.decode_book_catalog_code(book.catalog_code)[
                "category_sequence"
            ]
            == 0
        )
        previous = book.catalog_code
        book.title += " সম্পাদিত"
        book.save()
        book.refresh_from_db()
        assert book.catalog_code == previous
    assert len(set(original_codes + [book.catalog_code for book in overflow])) == 5
    for book, code in zip(books, original_codes, strict=True):
        book.refresh_from_db()
        assert book.catalog_code == code


def test_overflow_catalog_codes_validate_checksum_and_capacity(monkeypatch):
    from apps.catalog.models import catalog_code_overflow as overflow

    sequence = catalog_codes.BOOK_SEQUENCE_MASK + 1
    code = overflow.allocate_unassigned_code({sequence - 1})
    assert catalog_codes.decode_book_catalog_code(code)["book_sequence"] == sequence
    payload = catalog_codes.unscramble_payload(
        catalog_codes.int_from_catalog_code(code),
        inverse_multiplier=catalog_codes.BOOK_SCRAMBLE_INVERSE,
        offset=catalog_codes.BOOK_SCRAMBLE_OFFSET,
    )
    with pytest.raises(ValueError, match="payload is invalid"):
        overflow.unassigned_payload(payload ^ 1)
    monkeypatch.setattr(overflow, "UNASSIGNED_SEQUENCE_LIMIT", sequence)
    with pytest.raises(ValueError, match="capacity exceeded"):
        overflow.allocate_unassigned_code({sequence})
