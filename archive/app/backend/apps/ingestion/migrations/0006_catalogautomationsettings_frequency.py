from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0005_booksubmission_origin_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogautomationsettings",
            name="frequency",
            field=models.CharField(
                choices=[
                    ("daily", "Daily"),
                    ("weekly", "Weekly"),
                    ("biweekly", "Bi-weekly"),
                    ("monthly", "Monthly"),
                    ("bimonthly", "Bi-monthly"),
                    ("quarterly", "Every 3 months"),
                    ("four_monthly", "Every 4 months"),
                    ("half_yearly", "Half-yearly"),
                ],
                default="daily",
                max_length=24,
            ),
        ),
    ]
