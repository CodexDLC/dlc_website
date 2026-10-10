"""Добавить неоплачиваемую фотодокументацию с учётом времени."""

from decimal import Decimal

from django.db import migrations


def seed_photo_documentation(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    WorkType.objects.using(schema_editor.connection.alias).update_or_create(
        code="photo-documentation",
        defaults={
            "name_de": "Erstellung der Fotodokumentation",
            "name_ru": "Фотодокументация выполненных работ",
            "direction": "ac",
            "unit": "hour",
            "calculation_rule": "zero",
            "price_mode": "zero",
            "normative_hours": Decimal("0"),
            "unit_price": Decimal("0"),
            "underconstruction_hours": Decimal("0"),
            "is_break": False,
            "is_active": True,
            "sort_order": 15,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0009_seed_hpas_connection")]
    operations = [migrations.RunPython(seed_photo_documentation, migrations.RunPython.noop)]
