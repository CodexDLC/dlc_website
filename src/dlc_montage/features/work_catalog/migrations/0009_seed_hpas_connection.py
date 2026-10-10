"""Добавить подключение кабелей к шине уравнивания потенциалов."""

from decimal import Decimal

from django.db import migrations


def seed_hpas_connection(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    WorkType.objects.using(schema_editor.connection.alias).update_or_create(
        code="hpas-anschluss",
        defaults={
            "name_de": "Anschluss an die Potentialausgleichsschiene",
            "name_ru": "Подключение к шине уравнивания потенциалов",
            "direction": "ac",
            "unit": "piece",
            "calculation_rule": "connection",
            "price_mode": "per_norm_hour",
            "normative_hours": Decimal("0"),
            "unit_price": Decimal("40"),
            "underconstruction_hours": Decimal("0"),
            "is_break": False,
            "is_active": True,
            "sort_order": 10,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0008_mounting_price_mode")]
    operations = [migrations.RunPython(seed_hpas_connection, migrations.RunPython.noop)]
