from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_book_manual_metadata_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bookcontributor",
            name="role",
            field=models.CharField(
                choices=[
                    ("author", "Author"),
                    ("translator", "Translator"),
                    ("compiler", "Compiler"),
                    ("editor", "Editor"),
                    ("illustrator", "Illustrator"),
                    ("cover_artist", "Cover artist"),
                    ("publisher", "Publisher"),
                    ("other", "Other"),
                ],
                default="author",
                max_length=32,
            ),
        ),
    ]
