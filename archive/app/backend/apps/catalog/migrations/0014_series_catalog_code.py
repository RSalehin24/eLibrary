from django.db import migrations, models


CATALOG_CODE_LENGTH = 10
CATALOG_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CATALOG_CODE_BASE = len(CATALOG_CODE_ALPHABET)
CATALOG_CODE_MODULUS = CATALOG_CODE_BASE**CATALOG_CODE_LENGTH
CATALOG_CODE_TOTAL_BITS = CATALOG_CODE_LENGTH * 5
ENTITY_SEQUENCE_BITS = 16
ENTITY_TAG_BITS = 2
ENTITY_SALT_BITS = CATALOG_CODE_TOTAL_BITS - ENTITY_TAG_BITS - ENTITY_SEQUENCE_BITS
ENTITY_SEQUENCE_MASK = (1 << ENTITY_SEQUENCE_BITS) - 1
SERIES_ENTITY_TAG = 0
ENTITY_SCRAMBLE_MULTIPLIER = 741_103_597_443
SERIES_SCRAMBLE_OFFSET = 187_446_330_823


def code_salt(sequence_number, entity_tag):
    return ((sequence_number * 2_654_435_761) ^ (entity_tag * 2_246_822_519)) & ((1 << ENTITY_SALT_BITS) - 1)


def catalog_code_from_int(value):
    digits = []
    remaining = value
    for _ in range(CATALOG_CODE_LENGTH):
        remaining, remainder = divmod(remaining, CATALOG_CODE_BASE)
        digits.append(CATALOG_CODE_ALPHABET[remainder])
    return "".join(reversed(digits))


def scramble_payload(payload, *, multiplier, offset):
    return (payload * multiplier + offset) % CATALOG_CODE_MODULUS


def build_series_catalog_code(sequence_number):
    if sequence_number < 0 or sequence_number > ENTITY_SEQUENCE_MASK:
        raise ValueError("Entity catalog code capacity exceeded.")
    payload = (
        (SERIES_ENTITY_TAG << (ENTITY_SEQUENCE_BITS + ENTITY_SALT_BITS))
        | (sequence_number << ENTITY_SALT_BITS)
        | code_salt(sequence_number, SERIES_ENTITY_TAG)
    )
    return catalog_code_from_int(
        scramble_payload(
            payload,
            multiplier=ENTITY_SCRAMBLE_MULTIPLIER,
            offset=SERIES_SCRAMBLE_OFFSET,
        )
    )


def backfill_series_catalog_codes(apps, schema_editor):
    Series = apps.get_model("catalog", "Series")
    for index, series in enumerate(
        Series.objects.order_by("created_at", "name", "id"),
        start=1,
    ):
        Series.objects.filter(pk=series.pk).update(
            catalog_code=build_series_catalog_code(index)
        )


def alter_series_catalog_code_column(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f'ALTER TABLE "catalog_series" '
            f'ALTER COLUMN "catalog_code" TYPE varchar({CATALOG_CODE_LENGTH})'
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0013_curated_book_documents"),
    ]

    operations = [
        migrations.AddField(
            model_name="series",
            name="catalog_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=CATALOG_CODE_LENGTH,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(
            backfill_series_catalog_codes, migrations.RunPython.noop
        ),
        migrations.RunPython(
            alter_series_catalog_code_column, migrations.RunPython.noop
        ),
    ]
