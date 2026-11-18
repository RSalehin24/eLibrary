from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0019_alter_booksource_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="last_kindle_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
