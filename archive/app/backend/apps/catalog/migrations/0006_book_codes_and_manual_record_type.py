from django.db import migrations, models


CATALOG_CODE_LENGTH = 10
CATALOG_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CATALOG_CODE_BASE = len(CATALOG_CODE_ALPHABET)
CATALOG_CODE_MODULUS = CATALOG_CODE_BASE**CATALOG_CODE_LENGTH
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
CATEGORY_ENTITY_TAG = 1
WRITER_ENTITY_TAG = 2
BOOK_PAYLOAD_TAG = 3
ENTITY_SCRAMBLE_MULTIPLIER = 741_103_597_443
BOOK_SCRAMBLE_MULTIPLIER = 853_731_903_539
CATEGORY_SCRAMBLE_OFFSET = 94_518_223_171
WRITER_SCRAMBLE_OFFSET = 312_709_884_719
BOOK_SCRAMBLE_OFFSET = 608_198_411_427


def code_salt(sequence_number, entity_tag):
    return ((sequence_number * 2_654_435_761) ^ (entity_tag * 2_246_822_519)) & ((1 << ENTITY_SALT_BITS) - 1)


def book_payload_check(category_sequence, writer_sequence, book_sequence):
    return (
        (
            (category_sequence * 73)
            ^ (writer_sequence * 151)
            ^ (book_sequence * 197)
            ^ (BOOK_PAYLOAD_TAG * 29)
        )
        & BOOK_CHECK_MASK
    )


def catalog_code_from_int(value):
    digits = []
    remaining = value
    for _ in range(CATALOG_CODE_LENGTH):
        remaining, remainder = divmod(remaining, CATALOG_CODE_BASE)
        digits.append(CATALOG_CODE_ALPHABET[remainder])
    return "".join(reversed(digits))


def scramble_payload(payload, *, multiplier, offset):
    return (payload * multiplier + offset) % CATALOG_CODE_MODULUS


def build_entity_catalog_code(sequence_number, *, entity_tag):
    if sequence_number < 0 or sequence_number > ENTITY_SEQUENCE_MASK:
        raise ValueError("Entity catalog code capacity exceeded.")
    payload = (
        (entity_tag << (ENTITY_SEQUENCE_BITS + ENTITY_SALT_BITS))
        | (sequence_number << ENTITY_SALT_BITS)
        | code_salt(sequence_number, entity_tag)
    )
    offset = CATEGORY_SCRAMBLE_OFFSET if entity_tag == CATEGORY_ENTITY_TAG else WRITER_SCRAMBLE_OFFSET
    return catalog_code_from_int(
        scramble_payload(
            payload,
            multiplier=ENTITY_SCRAMBLE_MULTIPLIER,
            offset=offset,
        )
    )


def build_category_catalog_code(sequence_number):
    return build_entity_catalog_code(sequence_number, entity_tag=CATEGORY_ENTITY_TAG)


def build_writer_catalog_code(sequence_number):
    return build_entity_catalog_code(sequence_number, entity_tag=WRITER_ENTITY_TAG)


def build_book_catalog_code(category_sequence, writer_sequence, book_sequence):
    if book_sequence < 1 or book_sequence > BOOK_SEQUENCE_MASK:
        raise ValueError("Book catalog code capacity exceeded.")
    payload = (
        (BOOK_PAYLOAD_TAG << (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS + (ENTITY_SEQUENCE_BITS * 2)))
        | (category_sequence << (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS + ENTITY_SEQUENCE_BITS))
        | (writer_sequence << (BOOK_CHECK_BITS + BOOK_SEQUENCE_BITS))
        | (book_sequence << BOOK_CHECK_BITS)
        | book_payload_check(category_sequence, writer_sequence, book_sequence)
    )
    return catalog_code_from_int(
        scramble_payload(
            payload,
            multiplier=BOOK_SCRAMBLE_MULTIPLIER,
            offset=BOOK_SCRAMBLE_OFFSET,
        )
    )


def backfill_catalog_codes(apps, schema_editor):
    Book = apps.get_model("catalog", "Book")
    BookCategory = apps.get_model("catalog", "BookCategory")
    BookContributor = apps.get_model("catalog", "BookContributor")
    Category = apps.get_model("catalog", "Category")
    Contributor = apps.get_model("catalog", "Contributor")

    contributor_sequence_map = {}
    for index, contributor in enumerate(Contributor.objects.order_by("created_at", "name", "id"), start=1):
        contributor_sequence_map[contributor.pk] = index
        Contributor.objects.filter(pk=contributor.pk).update(catalog_code=build_writer_catalog_code(index))

    category_sequence_map = {}
    for index, category in enumerate(Category.objects.order_by("created_at", "name", "id"), start=1):
        category_sequence_map[category.pk] = index
        Category.objects.filter(pk=category.pk).update(catalog_code=build_category_catalog_code(index))

    primary_category_sequences = {}
    for book_id, category_id in BookCategory.objects.order_by("book_id", "category__name", "id").values_list("book_id", "category_id"):
        primary_category_sequences.setdefault(book_id, category_sequence_map.get(category_id, UNKNOWN_RELATION_SEQUENCE))

    primary_writer_sequences = {}
    for book_id, contributor_id in (
        BookContributor.objects.filter(role="author")
        .order_by("book_id", "sort_order", "contributor__name", "id")
        .values_list("book_id", "contributor_id")
    ):
        primary_writer_sequences.setdefault(book_id, contributor_sequence_map.get(contributor_id, UNKNOWN_RELATION_SEQUENCE))

    pair_counters = {}
    for book in Book.objects.order_by("created_at", "title", "id"):
        pair = (
            primary_category_sequences.get(book.pk, UNKNOWN_RELATION_SEQUENCE),
            primary_writer_sequences.get(book.pk, UNKNOWN_RELATION_SEQUENCE),
        )
        next_sequence = pair_counters.get(pair, 0) + 1
        pair_counters[pair] = next_sequence
        Book.objects.filter(pk=book.pk).update(catalog_code=build_book_catalog_code(pair[0], pair[1], next_sequence))


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_expand_url_field_lengths"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="catalog_code",
            field=models.CharField(blank=True, db_index=True, max_length=CATALOG_CODE_LENGTH, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="book",
            name="record_type",
            field=models.CharField(
                choices=[("digital", "Digital"), ("manual", "Manual")],
                db_index=True,
                default="digital",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="catalog_code",
            field=models.CharField(blank=True, db_index=True, max_length=CATALOG_CODE_LENGTH, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="contributor",
            name="catalog_code",
            field=models.CharField(blank=True, db_index=True, max_length=CATALOG_CODE_LENGTH, null=True, unique=True),
        ),
        migrations.RunPython(backfill_catalog_codes, migrations.RunPython.noop),
    ]
