from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0003_catalogautomationsettings_catalogcurationrun"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booksubmission",
            name="resolved_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name="matchcandidate",
            name="candidate_url",
            field=models.URLField(max_length=1000),
        ),
        migrations.AlterField(
            model_name="sourcecatalogentry",
            name="source_url",
            field=models.URLField(max_length=1000, unique=True),
        ),
        migrations.AlterField(
            model_name="titleresolutionattempt",
            name="resolved_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
