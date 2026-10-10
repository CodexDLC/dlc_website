"""Сохранить существующие длинные служебные действия при переходе на PostgreSQL."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mbg_reports", "0011_migrate_material_to_delivery_flat"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mbgreportrevision",
            name="action",
            field=models.CharField(max_length=64),
        ),
    ]
