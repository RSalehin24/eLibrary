from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processing', '0005_bookcreationrequest_force_generate'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookcreationrequest',
            name='has_multi_page_toc',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name='bookcreationrequest',
            name='source_toc_page_count',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='bookcreationrequest',
            name='fetched_toc_page_count',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
