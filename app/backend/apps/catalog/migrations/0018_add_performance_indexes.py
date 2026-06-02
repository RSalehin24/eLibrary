from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0017_book_empty_chapters_count"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="state",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("processing", "Processing"),
                    ("needs_review", "Needs review"),
                    ("ready", "Ready"),
                    ("published", "Published"),
                    ("archived", "Archived"),
                    ("soft_deleted", "Soft deleted"),
                ],
                default="draft",
                db_index=True,
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="book",
            name="review_state",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("needs_review", "Needs review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                db_index=True,
                max_length=32,
            ),
        ),
    ]
