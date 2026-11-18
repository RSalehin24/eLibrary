import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("access", "0004_alter_permissiongrant_options_and_more"),
        ("catalog", "0013_curated_book_documents"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="bookmark",
            name="chapter_href",
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AddField(
            model_name="bookmark",
            name="chapter_label",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="bookmark",
            name="preview_text",
            field=models.CharField(blank=True, max_length=280),
        ),
        migrations.CreateModel(
            name="Highlight",
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
                ("cfi_range", models.CharField(max_length=1024)),
                ("chapter_href", models.CharField(blank=True, max_length=512)),
                ("chapter_label", models.CharField(blank=True, max_length=255)),
                ("text", models.TextField()),
                ("note", models.TextField(blank=True)),
                (
                    "color",
                    models.CharField(
                        choices=[
                            ("yellow", "Yellow"),
                            ("green", "Green"),
                            ("blue", "Blue"),
                            ("pink", "Pink"),
                            ("underline", "Underline"),
                        ],
                        default="yellow",
                        max_length=16,
                    ),
                ),
                ("tags", models.JSONField(blank=True, default=list)),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="highlights",
                        to="catalog.book",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="highlights",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="highlight",
            index=models.Index(
                fields=["user", "-created_at"], name="access_high_user_id_b27ba2_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="highlight",
            index=models.Index(
                fields=["user", "book"], name="access_high_user_id_b1f6d2_idx"
            ),
        ),
    ]
