from . import catalog_codes as codes

UNASSIGNED_BOOK_TAG = 2
UNASSIGNED_SEQUENCE_BITS = (
    codes.CATALOG_CODE_TOTAL_BITS - codes.BOOK_TAG_BITS - codes.BOOK_CHECK_BITS
)
UNASSIGNED_SEQUENCE_LIMIT = (1 << UNASSIGNED_SEQUENCE_BITS) - 1


def unassigned_payload(payload):
    tag = payload >> (UNASSIGNED_SEQUENCE_BITS + codes.BOOK_CHECK_BITS)
    sequence = (payload >> codes.BOOK_CHECK_BITS) & UNASSIGNED_SEQUENCE_LIMIT
    check = payload & codes.BOOK_CHECK_MASK
    if (
        tag != UNASSIGNED_BOOK_TAG
        or sequence <= codes.BOOK_SEQUENCE_MASK
        or check != codes.book_payload_check(0, 0, sequence)
    ):
        raise ValueError("Book catalog code payload is invalid.")
    return {"category_sequence": 0, "writer_sequence": 0, "book_sequence": sequence}


def allocate_unassigned_code(sequences):
    sequence = max(sequences, default=codes.BOOK_SEQUENCE_MASK) + 1
    if sequence > UNASSIGNED_SEQUENCE_LIMIT:
        raise ValueError("Unassigned book catalog code capacity exceeded.")
    # This reserved book tag keeps all existing ten-character codes unchanged.
    payload = (
        UNASSIGNED_BOOK_TAG << (UNASSIGNED_SEQUENCE_BITS + codes.BOOK_CHECK_BITS)
        | sequence << codes.BOOK_CHECK_BITS
        | codes.book_payload_check(0, 0, sequence)
    )
    return codes.catalog_code_from_int(
        codes.scramble_payload(
            payload,
            multiplier=codes.BOOK_SCRAMBLE_MULTIPLIER,
            offset=codes.BOOK_SCRAMBLE_OFFSET,
        )
    )
