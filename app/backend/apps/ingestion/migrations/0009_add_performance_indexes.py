from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0008_booksubmission_deleted_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booksubmission",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("pending_resolution", "Pending resolution"),
                    ("queued", "Queued"),
                    ("processing", "Processing"),
                    ("needs_review", "Needs review"),
                    ("ready", "Ready"),
                    ("failed", "Failed"),
                    ("cancelled", "Cancelled"),
                    ("duplicate", "Duplicate candidate"),
                    ("deleted", "Deleted"),
                ],
                default="draft",
                db_index=True,
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="processingjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("processing", "Processing"),
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                    ("cancelled", "Cancelled"),
                ],
                default="queued",
                db_index=True,
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="processingjob",
            name="job_type",
            field=models.CharField(
                choices=[
                    ("resolution", "Resolution"),
                    ("ingestion", "Ingestion"),
                    ("reprocess", "Reprocess"),
                ],
                default="ingestion",
                db_index=True,
                max_length=24,
            ),
        ),
    ]
