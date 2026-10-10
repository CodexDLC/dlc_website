"""Обновление сдельных расценок каталога AC на базе 35 EUR/час."""

from decimal import Decimal

from django.db import migrations

WORKS_UPDATE = [
    ("wr-montage", "1.00", "35.00", "per_unit"),
    ("uv-montage", "1.00", "35.00", "per_unit"),
    ("nh-montage", "1.00", "30.00", "per_unit"),
    ("cable-tray", "2.00", "70.00", "per_unit"),
    ("wr-anschluss", "1.00", "35.00", "per_unit"),
    ("uv-anschluss", "1.00", "40.00", "per_unit"),
    ("nh-anschluss", "1.25", "50.00", "per_unit"),
    ("kabeldurchfuehrung", "1.00", "35.00", "per_unit"),
    ("potential", "0.50", "20.00", "per_unit"),
    ("hpas-anschluss", "0.50", "20.00", "per_unit"),
    ("erder", "2.50", "90.00", "per_unit"),
    ("kernlochbohrung", "3.00", "120.00", "per_unit"),
    ("licht", "0.00", "40.00", "actual_hourly"),
    ("material", "0.00", "40.00", "actual_hourly"),
    ("sonstige", "0.00", "40.00", "actual_hourly"),
]

CABLES_UPDATE = [
    ("data", "1.50", "55.00"),
    ("pe-1x16", "1.50", "55.00"),
    ("control-7x1-5", "1.50", "55.00"),
    ("power-5x10", "2.00", "70.00"),
    ("power-5x16", "2.00", "70.00"),
    ("power-5x25", "2.00", "70.00"),
    ("power-5x35", "1.50", "50.00"),
    ("power-5x50", "1.50", "50.00"),
]


def update_catalog_rates(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    CableType = apps.get_model("work_catalog", "CableType")
    alias = schema_editor.connection.alias

    for code, norm, price, price_mode in WORKS_UPDATE:
        WorkType.objects.using(alias).filter(code=code).update(
            normative_hours=Decimal(norm),
            unit_price=Decimal(price),
            price_mode=price_mode,
        )

    for code, norm, price in CABLES_UPDATE:
        CableType.objects.using(alias).filter(code=code).update(
            normative_hours_per_ten_meters=Decimal(norm),
            unit_price_per_ten_meters=Decimal(price),
        )


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0011_seed_uv_hpas_route")]
    operations = [migrations.RunPython(update_catalog_rates, migrations.RunPython.noop)]
