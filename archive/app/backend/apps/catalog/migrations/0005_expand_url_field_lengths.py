from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_backfill_unicode_safe_catalog_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="cover_source_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name="booksource",
            name="normalized_source_url",
            field=models.URLField(max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name="booksource",
            name="source_url",
            field=models.URLField(max_length=1000),
        ),
    ]
