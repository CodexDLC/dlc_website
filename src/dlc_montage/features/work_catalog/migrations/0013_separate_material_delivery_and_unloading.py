"""Разделение доставки материала (50 EUR паушаль) и разгрузки (0 EUR, только часы)."""

from decimal import Decimal

from django.db import migrations


def seed_material_split(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    alias = schema_editor.connection.alias

    # 1. Заезд и доставка материала (фиксированная паушальная выплата 50 EUR)
    WorkType.objects.using(alias).update_or_create(
        code="material-delivery",
        defaults={
            "name_de": "Materialabholung und Anlieferung",
            "name_ru": "Заезд и доставка материала",
            "direction": "both",
            "unit": "flat",
            "calculation_rule": "fixed",
            "price_mode": "per_unit",
            "normative_hours": Decimal("0.00"),
            "unit_price": Decimal("50.00"),
            "underconstruction_hours": Decimal("0.00"),
            "is_break": False,
            "is_active": True,
            "sort_order": 13,
        },
    )

    # 2. Разгрузка материала на объекте (не оплачивается на сдельщине, только учёт рабочего времени)
    WorkType.objects.using(alias).update_or_create(
        code="material-unloading",
        defaults={
            "name_de": "Materialentladung auf der Baustelle",
            "name_ru": "Разгрузка материала на объекте",
            "direction": "both",
            "unit": "hour",
            "calculation_rule": "zero",
            "price_mode": "zero",
            "normative_hours": Decimal("0.00"),
            "unit_price": Decimal("0.00"),
            "underconstruction_hours": Decimal("0.00"),
            "is_break": False,
            "is_active": True,
            "sort_order": 14,
        },
    )

    # 3. Сохраняем "material" активным для совместимости с историческими тестами и отчётами
    pass


def rollback_material_split(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    alias = schema_editor.connection.alias

    WorkType.objects.using(alias).filter(code__in=["material-delivery", "material-unloading"]).delete()
    WorkType.objects.using(alias).filter(code="material").update(
        is_active=True,
        name_de="Materialabholung und Materialtransport",
        name_ru="Забор и доставка материала",
    )


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0012_update_piecework_35_eur_rates")]
    operations = [migrations.RunPython(seed_material_split, rollback_material_split)]
