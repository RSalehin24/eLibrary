from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0021_userbookkindlesend"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="book",
            name="last_kindle_sent_at",
        ),
    ]
