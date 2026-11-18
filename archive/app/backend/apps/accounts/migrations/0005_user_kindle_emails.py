from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_user_email_setup_pending_and_nonce"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="kindle_emails",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
