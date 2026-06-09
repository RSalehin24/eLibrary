import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0020_book_last_kindle_sent_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserBookKindleSend",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kindle_sends", to=settings.AUTH_USER_MODEL)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kindle_sends", to="catalog.book")),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("user", "book")},
            },
        ),
    ]
