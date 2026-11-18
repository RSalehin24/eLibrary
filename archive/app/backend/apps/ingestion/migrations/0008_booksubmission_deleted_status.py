from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0007_sourcecatalogrefreshstate"),
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
                max_length=32,
            ),
        ),
    ]
