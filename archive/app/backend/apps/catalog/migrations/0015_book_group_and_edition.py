import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0014_series_catalog_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("canonical_title", models.CharField(max_length=255)),
                (
                    "normalized_canonical_title",
                    models.CharField(blank=True, db_index=True, default="", editable=False, max_length=255),
                ),
                ("note", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["canonical_title"],
            },
        ),
        migrations.AddField(
            model_name="book",
            name="edition",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="book",
            name="normalized_edition",
            field=models.CharField(blank=True, db_index=True, default="", editable=False, max_length=120),
        ),
        migrations.AddField(
            model_name="book",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="books",
                to="catalog.bookgroup",
            ),
        ),
    ]
