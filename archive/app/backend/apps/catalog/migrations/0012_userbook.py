import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_user_books(apps, schema_editor):
    BookSubmission = apps.get_model("ingestion", "BookSubmission")
    UserBook = apps.get_model("catalog", "UserBook")
    existing_pairs = set(UserBook.objects.values_list("user_id", "book_id"))
    user_books = []
    submissions = (
        BookSubmission.objects.filter(submitter_id__isnull=False, linked_book_id__isnull=False)
        .order_by("created_at", "id")
        .values("submitter_id", "linked_book_id", "created_at", "updated_at")
    )
    for submission in submissions.iterator():
        pair = (submission["submitter_id"], submission["linked_book_id"])
        if pair in existing_pairs:
            continue
        existing_pairs.add(pair)
        user_books.append(
            UserBook(
                user_id=pair[0],
                book_id=pair[1],
                created_at=submission["created_at"],
                updated_at=submission["updated_at"],
            )
        )
    UserBook.objects.bulk_create(user_books, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_remove_book_source_normalized_title_constraint"),
        ("ingestion", "0008_booksubmission_deleted_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserBook",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_books", to="catalog.book")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="my_books", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("user", "book")},
            },
        ),
        migrations.RunPython(backfill_user_books, migrations.RunPython.noop),
    ]
