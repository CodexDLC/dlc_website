"""Монтажные позиции временно оцениваются по нормативу 40 евро за человеко-час."""

from django.db import migrations


def update_mounting_prices(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    WorkType.objects.using(schema_editor.connection.alias).filter(
        code__in=("wr-montage", "uv-montage", "nh-montage")
    ).update(price_mode="per_norm_hour", unit_price=40)


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0007_seed_structured_ac_catalog")]
    operations = [migrations.RunPython(update_mounting_prices, migrations.RunPython.noop)]
