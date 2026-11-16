from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="repository",
            name="url",
            field=models.URLField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
                verbose_name="URL",
            ),
        ),
    ]
