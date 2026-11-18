from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0016_alter_generatedasset_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="empty_chapters_count",
            field=models.IntegerField(default=0),
        ),
    ]
