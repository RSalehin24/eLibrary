from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0009_bookcontributor_compiler_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="content_items",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
