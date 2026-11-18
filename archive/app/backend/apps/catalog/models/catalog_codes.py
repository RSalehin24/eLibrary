CATALOG_CODE_LENGTH = 10
CATALOG_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CATALOG_CODE_BASE = len(CATALOG_CODE_ALPHABET)
CATALOG_CODE_MODULUS = CATALOG_CODE_BASE**CATALOG_CODE_LENGTH
CATALOG_CODE_INDEX = {char: index for index, char in enumerate(CATALOG_CODE_ALPHABET)}
CATALOG_CODE_TOTAL_BITS = CATALOG_CODE_LENGTH * 5
ENTITY_SEQUENCE_BITS = 16
BOOK_SEQUENCE_BITS = 12
ENTITY_TAG_BITS = 2
BOOK_TAG_BITS = 2
ENTITY_SALT_BITS = CATALOG_CODE_TOTAL_BITS - ENTITY_TAG_BITS - ENTITY_SEQUENCE_BITS
BOOK_CHECK_BITS = CATALOG_CODE_TOTAL_BITS - (BOOK_TAG_BITS + (ENTITY_SEQUENCE_BITS * 2) + BOOK_SEQUENCE_BITS)
ENTITY_SEQUENCE_MASK = (1 << ENTITY_SEQUENCE_BITS) - 1
BOOK_SEQUENCE_MASK = (1 << BOOK_SEQUENCE_BITS) - 1
BOOK_CHECK_MASK = (1 << BOOK_CHECK_BITS) - 1
UNKNOWN_RELATION_SEQUENCE = 0
SERIES_ENTITY_TAG = 0
CATEGORY_ENTITY_TAG = 1
WRITER_ENTITY_TAG = 2
BOOK_PAYLOAD_TAG = 3
ENTITY_SCRAMBLE_MULTIPLIER = 741_103_597_443
BOOK_SCRAMBLE_MULTIPLIER = 853_731_903_539
ENTITY_SCRAMBLE_INVERSE = pow(ENTITY_SCRAMBLE_MULTIPLIER, -1, CATALOG_CODE_MODULUS)
BOOK_SCRAMBLE_INVERSE = pow(BOOK_SCRAMBLE_MULTIPLIER, -1, CATALOG_CODE_MODULUS)
CATEGORY_SCRAMBLE_OFFSET = 94_518_223_171
WRITER_SCRAMBLE_OFFSET = 312_709_884_719
SERIES_SCRAMBLE_OFFSET = 187_446_330_823
BOOK_SCRAMBLE_OFFSET = 608_198_411_427

_ENTITY_SCRAMBLE_OFFSETS = {
    SERIES_ENTITY_TAG: SERIES_SCRAMBLE_OFFSET,
    CATEGORY_ENTITY_TAG: CATEGORY_SCRAMBLE_OFFSET,
    WRITER_ENTITY_TAG: WRITER_SCRAMBLE_OFFSET,
}


def code_salt(sequence_number, entity_tag):
    return ((sequence_number * 2_654_435_761) ^ (entity_tag * 2_246_822_519)) & ((1 << ENTITY_SALT_BITS) - 1)


def book_payload_check(category_sequence, writer_sequence, book_sequence):
    return (
        ((category_sequence * 73) ^ (writer_sequence * 151) ^ (book_sequence * 197) ^ (BOOK_PAYLOAD_TAG * 29))
        & BOOK_CHECK_MASK
    )


def catalog_code_from_int(value):
    if value < 0 or value >= CATALOG_CODE_MODULUS:
        raise ValueError("Catalog code value is outside the supported range.")
    digits = []
    remaining = value
    for _ in range(CATALOG_CODE_LENGTH):
        remaining, remainder = divmod(remaining, CATALOG_CODE_BASE)
        digits.append(CATALOG_CODE_ALPHABET[remainder])
    return "".join(reversed(digits))


def int_from_catalog_code(value):
    code = (value or "").strip().upper()
    if len(code) != CATALOG_CODE_LENGTH:
        raise ValueError("Catalog code has the wrong length.")
    numeric_value = 0
    for char in code:
        if char not in CATALOG_CODE_INDEX:
            raise ValueError("Catalog code contains unsupported characters.")
        numeric_value = (numeric_value * CATALOG_CODE_BASE) + CATALOG_CODE_INDEX[char]
    return numeric_value


def scramble_payload(payload, *, multiplier, offset):
    return (payload * multiplier + offset) % CATALOG_CODE_MODULUS


def unscramble_payload(scrambled_value, *, inverse_multiplier, offset):
    return ((scrambled_value - offset) * inverse_multiplier) % CATALOG_CODE_MODULUS


def build_entity_catalog_code(sequence_number, *, entity_tag):
    if sequence_number < 0 or sequence_number > ENTITY_SEQUENCE_MASK:
        raise ValueError("Entity catalog code capacity exceeded.")
    if entity_tag not in _ENTITY_SCRAMBLE_OFFSETS:
        raise ValueError("Unknown entity tag.")
    payload = ((entity_tag << (ENTITY_SEQUENCE_BITS + ENTITY_SALT_BITS)) | (sequence_number << ENTITY_SALT_BITS) | code_salt(sequence_number, entity_tag))
    offset = _ENTITY_SCRAMBLE_OFFSETS[entity_tag]
    return catalog_code_from_int(scramble_payload(payload, multiplier=ENTITY_SCRAMBLE_MULTIPLIER, offset=offset))


def decode_entity_catalog_code(value, *, entity_tag):
    if entity_tag not in _ENTITY_SCRAMBLE_OFFSETS:
        raise ValueError("Unknown entity tag.")
    offset = _ENTITY_SCRAMBLE_OFFSETS[entity_tag]
    payload = unscramble_payload(int_from_catalog_code(value), inverse_multiplier=ENTITY_SCRAMBLE_INVERSE, offset=offset)
    actual_tag = payload >> (ENTITY_SEQUENCE_BITS + ENTITY_SALT_BITS)
    sequence_number = (payload >> ENTITY_SALT_BITS) & ENTITY_SEQUENCE_MASK
    salt = payload & ((1 << ENTITY_SALT_BITS) - 1)
    if actual_tag != entity_tag or salt != code_salt(sequence_number, entity_tag):
        raise ValueError("Catalog code payload is invalid.")
    return sequence_number


def build_category_catalog_code(sequence_number):
    return build_entity_catalog_code(sequence_number, entity_tag=CATEGORY_ENTITY_TAG)


def build_writer_catalog_code(sequence_number):
    return build_entity_catalog_code(sequence_number, entity_tag=WRITER_ENTITY_TAG)


def build_series_catalog_code(sequence_number):
    return build_entity_catalog_code(sequence_number, entity_tag=SERIES_ENTITY_TAG)


def decode_category_catalog_code(value):
    return decode_entity_catalog_code(value, entity_tag=CATEGORY_ENTITY_TAG)


def decode_writer_catalog_code(value):
    return decode_entity_catalog_code(value, entity_tag=WRITER_ENTITY_TAG)


def decode_series_catalog_code(value):
    return decode_entity_catalog_code(value, entity_tag=SERIES_ENTITY_TAG)


def is_entity_catalog_code(value, *, entity_tag):
    try:
        decode_entity_catalog_code(value, entity_tag=entity_tag)
    except ValueError:
        return False
    return True


def next_entity_sequence(model, field_name, *, entity_tag, exclude_pk=None):
    queryset = model.objects.exclude(**{f"{field_name}__isnull": True}).exclude(**{field_name: ""})
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    latest_sequence = UNKNOWN_RELATION_SEQUENCE
    for code in queryset.values_list(field_name, flat=True).iterator():
        try:
            latest_sequence = max(latest_sequence, decode_entity_catalog_code(code, entity_tag=entity_tag))
        except ValueError:
            continue
    next_sequence = latest_sequence + 1
    if next_sequence > ENTITY_SEQUENCE_MASK:
        raise ValueError("Entity catalog code capacity exceeded.")
    return next_sequence


def primary_category_sequence_for_book(book):
    if not book.pk:
        return UNKNOWN_RELATION_SEQUENCE
    category_code = (
        book.book_categories.exclude(category__catalog_code__isnull=True)
        .exclude(category__catalog_code="")
        .select_related("category")
        .order_by("category__name")
        .values_list("category__catalog_code", flat=True)
        .first()
    )
    if not category_code:
        return UNKNOWN_RELATION_SEQUENCE
    try:
        return decode_category_catalog_code(category_code)
    except ValueError:
        return UNKNOWN_RELATION_SEQUENCE


def primary_writer_sequence_for_book(book):
    if not book.pk:
        return UNKNOWN_RELATION_SEQUENCE
    writer_code = (
        book.book_contributors.filter(role="author")
        .exclude(contributor__catalog_code__isnull=True)
        .exclude(contributor__catalog_code="")
        .select_related("contributor")
        .order_by("sort_order", "contributor__name")
        .values_list("contributor__catalog_code", flat=True)
        .first()
    )
    if not writer_code:
        return UNKNOWN_RELATION_SEQUENCE
    try:
        return decode_writer_catalog_code(writer_code)
    except ValueError:
        return UNKNOWN_RELATION_SEQUENCE


def decode_book_catalog_code(value):
    payload = unscramble_payload(int_from_catalog_code(value), inverse_multiplier=BOOK_SCRAMBLE_INVERSE, offset=BOOK_SCRAMBLE_OFFSET)
    check = payload & BOOK_CHECK_MASK
    book_sequence = (payload >> BOOK_CHECK_BITS) & BOOK_SEQUENCE_MASK
    writer_sequence = (payload >> (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS)) & ENTITY_SEQUENCE_MASK
    category_sequence = (payload >> (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS + ENTITY_SEQUENCE_BITS)) & ENTITY_SEQUENCE_MASK
    book_tag = payload >> (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS + (ENTITY_SEQUENCE_BITS * 2))
    if book_tag != BOOK_PAYLOAD_TAG or book_sequence == 0:
        raise ValueError("Book catalog code payload is invalid.")
    if check != book_payload_check(category_sequence, writer_sequence, book_sequence):
        raise ValueError("Book catalog code payload is invalid.")
    return {
        "category_sequence": category_sequence,
        "writer_sequence": writer_sequence,
        "book_sequence": book_sequence,
    }


def derive_category_catalog_code_from_book_code(value):
    decoded = decode_book_catalog_code(value)
    return build_category_catalog_code(decoded["category_sequence"])


def derive_writer_catalog_code_from_book_code(value):
    decoded = decode_book_catalog_code(value)
    return build_writer_catalog_code(decoded["writer_sequence"])


def is_book_catalog_code(value):
    try:
        decode_book_catalog_code(value)
    except ValueError:
        return False
    return True


def build_book_catalog_code(book):
    from .books import Book

    category_sequence = primary_category_sequence_for_book(book)
    writer_sequence = primary_writer_sequence_for_book(book)
    current_code = (book.catalog_code or "").strip().upper()
    if current_code:
        try:
            decoded = decode_book_catalog_code(current_code)
            if decoded["category_sequence"] == category_sequence and decoded["writer_sequence"] == writer_sequence:
                return current_code
        except ValueError:
            pass

    latest_sequence = UNKNOWN_RELATION_SEQUENCE
    queryset = Book.objects.exclude(pk=book.pk).exclude(catalog_code__isnull=True).exclude(catalog_code="")
    for existing_code in queryset.values_list("catalog_code", flat=True).iterator():
        try:
            decoded = decode_book_catalog_code(existing_code)
        except ValueError:
            continue
        if decoded["category_sequence"] == category_sequence and decoded["writer_sequence"] == writer_sequence:
            latest_sequence = max(latest_sequence, decoded["book_sequence"])

    next_sequence = latest_sequence + 1
    if next_sequence > BOOK_SEQUENCE_MASK:
        raise ValueError("Book catalog code capacity exceeded for this writer/category pair.")

    payload = (
        (BOOK_PAYLOAD_TAG << (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS + (ENTITY_SEQUENCE_BITS * 2)))
        | (category_sequence << (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS + ENTITY_SEQUENCE_BITS))
        | (writer_sequence << (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS))
        | (next_sequence << BOOK_CHECK_BITS)
        | book_payload_check(category_sequence, writer_sequence, next_sequence)
    )
    return catalog_code_from_int(scramble_payload(payload, multiplier=BOOK_SCRAMBLE_MULTIPLIER, offset=BOOK_SCRAMBLE_OFFSET))
