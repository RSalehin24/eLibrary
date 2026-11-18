from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_profile_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_setup_pending",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="password_setup_nonce",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
