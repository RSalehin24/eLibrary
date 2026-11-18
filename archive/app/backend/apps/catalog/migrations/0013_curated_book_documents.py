import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0008_booksubmission_deleted_status"),
        ("catalog", "0012_userbook"),
    ]

    operations = [
        migrations.CreateModel(
            name="CuratedBookDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_url", models.URLField(db_index=True, max_length=1000)),
                ("canonical_url", models.URLField(blank=True, max_length=1000)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("validated", "Validated"),
                            ("review_required", "Review required"),
                            ("invalid", "Invalid"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=24,
                    ),
                ),
                ("structure_type", models.CharField(blank=True, max_length=64)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("validation_summary", models.JSONField(blank=True, default=dict)),
                ("source_snapshot", models.JSONField(blank=True, default=dict)),
                ("document", models.JSONField(blank=True, default=dict)),
                (
                    "book",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="curated_documents",
                        to="catalog.book",
                    ),
                ),
                (
                    "source_job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="curated_documents",
                        to="ingestion.processingjob",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("source_url", "version")},
            },
        ),
        migrations.CreateModel(
            name="CuratedEntity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entity_type",
                    models.CharField(
                        choices=[
                            ("work", "Book/work"),
                            ("person", "Person"),
                            ("organization", "Organization"),
                            ("series", "Series"),
                            ("category", "Category"),
                            ("asset", "Asset"),
                            ("publication_event", "Publication event"),
                            ("metadata", "Metadata"),
                        ],
                        max_length=32,
                    ),
                ),
                ("role", models.CharField(blank=True, max_length=64)),
                ("value", models.CharField(max_length=500)),
                ("normalized_value", models.CharField(blank=True, db_index=True, max_length=500)),
                ("source_url", models.URLField(blank=True, max_length=1000)),
                ("source_location", models.CharField(blank=True, max_length=255)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence", models.FloatField(default=0)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entities",
                        to="catalog.curatedbookdocument",
                    ),
                ),
            ],
            options={"ordering": ["entity_type", "role", "value"]},
        ),
        migrations.CreateModel(
            name="CuratedSection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("section_id", models.CharField(max_length=160)),
                (
                    "section_type",
                    models.CharField(
                        choices=[
                            ("cover", "Cover"),
                            ("title_page", "Title page"),
                            ("book_info", "Book information"),
                            ("dedication", "Dedication"),
                            ("front_matter", "Front matter"),
                            ("generated_toc", "Generated TOC"),
                            ("body", "Body"),
                            ("back_matter", "Back matter"),
                        ],
                        max_length=32,
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=500)),
                ("path", models.JSONField(blank=True, default=list)),
                ("source_url", models.URLField(blank=True, max_length=1000)),
                ("source_location", models.CharField(blank=True, max_length=255)),
                ("html", models.TextField(blank=True)),
                ("confidence", models.FloatField(default=0)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="catalog.curatedbookdocument",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "section_id"],
                "unique_together": {("document", "section_id")},
            },
        ),
        migrations.CreateModel(
            name="CuratedEvidence",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("value", models.CharField(blank=True, max_length=500)),
                ("entity_type", models.CharField(blank=True, max_length=32)),
                ("role", models.CharField(blank=True, max_length=64)),
                ("source_url", models.URLField(blank=True, max_length=1000)),
                ("source_location", models.CharField(blank=True, max_length=255)),
                ("evidence_text", models.TextField(blank=True)),
                ("confidence", models.FloatField(default=0)),
                ("extractor", models.CharField(blank=True, max_length=120)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence",
                        to="catalog.curatedbookdocument",
                    ),
                ),
                (
                    "entity",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence",
                        to="catalog.curatedentity",
                    ),
                ),
                (
                    "section",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence",
                        to="catalog.curatedsection",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
