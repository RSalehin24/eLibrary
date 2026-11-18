from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0009_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="processingjob",
            name="worker_hostname",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
