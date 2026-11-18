from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0007_rehash_catalog_codes"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="manual_binding",
            field=models.CharField(
                blank=True,
                choices=[("hard_cover", "Hard Cover"), ("paper_back", "Paper Back")],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="manual_is_compilation",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="book",
            name="manual_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="book",
            name="manual_publisher",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
