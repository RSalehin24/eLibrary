from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0008_booksubmission_deleted_status"),
        ("processing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookrecord",
            name="source_catalog_entry",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processing_records",
                to="ingestion.sourcecatalogentry",
            ),
        ),
        migrations.AddField(
            model_name="bookcreationrequest",
            name="origin",
            field=models.CharField(
                choices=[
                    ("user", "User"),
                    ("curation", "Source curation"),
                    ("automation", "Daily automation"),
                ],
                db_index=True,
                default="curation",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="bookcreationrequest",
            name="submission",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processing_request",
                to="ingestion.booksubmission",
            ),
        ),
        migrations.AddField(
            model_name="processingsyncstate",
            name="task_id",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="processingsyncstate",
            name="queue_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="processingsyncstate",
            name="last_error",
            field=models.TextField(blank=True),
        ),
    ]
