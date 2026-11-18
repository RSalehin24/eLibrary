import datetime

import apps.processing.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0011_remove_book_source_normalized_title_constraint"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcessingAutomationSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "kind",
                    models.CharField(
                        choices=[("catalog", "Catalog"), ("incomplete", "Incomplete")],
                        max_length=32,
                        unique=True,
                    ),
                ),
                ("enabled", models.BooleanField(default=False)),
                ("interval", models.CharField(default="daily", max_length=32)),
                ("time", models.TimeField(default=datetime.time(2, 0))),
                ("saved", models.BooleanField(default=False)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("status_message", models.CharField(blank=True, max_length=500)),
            ],
            options={
                "ordering": ["kind"],
            },
        ),
        migrations.CreateModel(
            name="ProcessingSyncState",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("singleton_key", models.CharField(default="default", max_length=32, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("idle", "Idle"),
                            ("syncing", "Syncing"),
                            ("pausing", "Pausing"),
                            ("paused", "Paused"),
                        ],
                        default="idle",
                        max_length=32,
                    ),
                ),
                ("progress", models.JSONField(blank=True, null=True)),
                ("remote_pages", models.JSONField(blank=True, default=list)),
                ("page_index", models.PositiveIntegerField(default=0)),
                ("fetched_count", models.PositiveIntegerField(default=0)),
                ("skipped_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("appended_count", models.PositiveIntegerField(default=0)),
                ("message", models.CharField(default="Ready to sync.", max_length=500)),
            ],
            options={
                "ordering": ["singleton_key"],
            },
        ),
        migrations.CreateModel(
            name="BookRecord",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(
                        default=apps.processing.models.generate_processing_id,
                        max_length=120,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("url", models.URLField(max_length=1000, unique=True)),
                ("category", models.CharField(max_length=255)),
                ("writer", models.CharField(blank=True, max_length=255)),
                ("translator", models.CharField(blank=True, max_length=255)),
                ("composer", models.CharField(blank=True, max_length=255)),
                ("publisher", models.CharField(blank=True, max_length=255)),
                (
                    "book_creation_state",
                    models.CharField(
                        choices=[
                            ("not_created", "Not created"),
                            ("initial", "Initial"),
                            ("queued", "Queued"),
                            ("processing", "Processing"),
                            ("created", "Created"),
                            ("paused", "Paused"),
                            ("failed", "Failed"),
                            ("duplicate", "Duplicate"),
                            ("deleted", "Deleted"),
                        ],
                        db_index=True,
                        default="not_created",
                        max_length=32,
                    ),
                ),
                ("was_incomplete", models.BooleanField(default=False)),
                ("resolved_from_incomplete", models.BooleanField(default=False)),
                ("will_resolve_to_category", models.CharField(blank=True, max_length=255)),
                ("is_duplicate", models.BooleanField(default=False)),
                (
                    "duplicate_of_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="duplicate_records",
                        to="processing.bookrecord",
                    ),
                ),
                (
                    "linked_book",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="processing_book_records",
                        to="catalog.book",
                    ),
                ),
            ],
            options={
                "ordering": ["name", "id"],
            },
        ),
        migrations.CreateModel(
            name="BookCreationRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.CharField(
                        default=apps.processing.models.generate_processing_id,
                        max_length=120,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("initial", "Initial"),
                            ("queued", "Queued"),
                            ("processing", "Processing"),
                            ("created", "Created"),
                            ("paused", "Paused"),
                            ("failed", "Failed"),
                            ("duplicate", "Duplicate"),
                            ("deleted", "Deleted"),
                        ],
                        db_index=True,
                        default="initial",
                        max_length=32,
                    ),
                ),
                ("progress", models.JSONField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("is_resumed", models.BooleanField(default=False)),
                ("is_confirmed_not_duplicate", models.BooleanField(default=False)),
                ("duplicate_confirmed", models.BooleanField(default=False)),
                ("pipeline_outcome", models.CharField(default="created", max_length=32)),
                (
                    "book_record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="creation_requests",
                        to="processing.bookrecord",
                    ),
                ),
                (
                    "duplicate_of_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="duplicate_creation_requests",
                        to="processing.bookrecord",
                    ),
                ),
                (
                    "duplicate_of_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="duplicate_requests",
                        to="processing.bookcreationrequest",
                    ),
                ),
                (
                    "linked_book",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="processing_creation_requests",
                        to="catalog.book",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at", "-created_at", "id"],
            },
        ),
    ]
