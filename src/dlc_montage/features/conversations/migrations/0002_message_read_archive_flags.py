from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="is_archived",
            field=models.BooleanField(db_index=True, default=False, verbose_name="archived"),
        ),
        migrations.AddField(
            model_name="message",
            name="is_read",
            field=models.BooleanField(db_index=True, default=False, verbose_name="read"),
        ),
    ]
