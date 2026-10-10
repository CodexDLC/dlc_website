"""Согласованный структурированный каталог работ AC для прототипа MBG."""

# ruff: noqa: RUF001

from decimal import Decimal

from django.db import migrations

WORKS = [
    (
        "wr-montage",
        "Montage Wechselrichter",
        "Монтаж инвертора",
        "piece",
        "fixed",
        "per_norm_hour",
        "1",
        "40",
        "1",
        False,
    ),
    (
        "uv-montage",
        "Montage UV-PV",
        "Монтаж щита UV-PV",
        "piece",
        "fixed",
        "per_norm_hour",
        "1",
        "40",
        "1",
        False,
    ),
    (
        "nh-montage",
        "Montage NH-Verteiler",
        "Монтаж NH-распределителя",
        "piece",
        "fixed",
        "per_norm_hour",
        "1",
        "40",
        "1",
        False,
    ),
    (
        "cable-tray",
        "Montage Kabeltrasse",
        "Монтаж кабельной трассы",
        "ten_meters",
        "fixed",
        "per_unit",
        "2",
        "80",
        "0",
        False,
    ),
    ("cable-laying", "Kabelverlegung", "Прокладка кабеля", "ten_meters", "cable", "per_unit", "0", "0", "0", False),
    (
        "wr-anschluss",
        "Anschluss Wechselrichter",
        "Подключение инвертора",
        "piece",
        "connection",
        "per_norm_hour",
        "0",
        "40",
        "0",
        False,
    ),
    (
        "uv-anschluss",
        "Anschluss UV-PV",
        "Подключение UV-PV",
        "piece",
        "connection",
        "per_norm_hour",
        "0",
        "40",
        "0",
        False,
    ),
    (
        "nh-anschluss",
        "Anschluss NH-Verteiler",
        "Подключение NH-распределителя",
        "piece",
        "connection",
        "per_norm_hour",
        "0",
        "40",
        "0",
        False,
    ),
    (
        "erder",
        "Errichten eines Tiefenerders",
        "Устройство глубинного заземлителя",
        "piece",
        "fixed",
        "per_unit",
        "2.5",
        "100",
        "0",
        False,
    ),
    (
        "potential",
        "Montage neue HPAS",
        "Монтаж новой шины уравнивания потенциалов",
        "piece",
        "fixed",
        "per_unit",
        "0.5",
        "20",
        "0",
        False,
    ),
    (
        "kernlochbohrung",
        "Kernlochbohrung",
        "Алмазное сверление отверстия",
        "piece",
        "fixed",
        "per_unit",
        "3",
        "160",
        "0",
        False,
    ),
    (
        "kabeldurchfuehrung",
        "Herstellen einer Kabeldurchführung",
        "Устройство сложного кабельного прохода",
        "piece",
        "fixed",
        "per_unit",
        "1",
        "40",
        "0",
        False,
    ),
    (
        "licht",
        "Umsetzen vorhandener Beleuchtung",
        "Перенос существующего освещения",
        "hour",
        "actual",
        "actual_hourly",
        "0",
        "40",
        "0",
        False,
    ),
    (
        "material",
        "Materialabholung und Materialtransport",
        "Забор и доставка материала",
        "hour",
        "actual",
        "actual_hourly",
        "0",
        "40",
        "0",
        False,
    ),
    ("sonstige", "Sonstige Tätigkeit", "Прочая работа", "hour", "actual", "actual_hourly", "0", "40", "0", False),
    (
        "freiraeumen",
        "Freiräumen des Montagebereichs",
        "Освобождение зоны монтажа",
        "hour",
        "zero",
        "zero",
        "0",
        "0",
        "0",
        False,
    ),
    ("wartezeit", "Wartezeit", "Ожидание", "hour", "zero", "zero", "0", "0", "0", False),
    ("mittagspause", "Mittagspause", "Обеденный перерыв", "hour", "zero", "zero", "0", "0", "0", True),
]

CABLES = [
    ("data", "Datenleitung", "Кабель данных", "data", "1.5", "55"),
    ("pe-1x16", "PE-Leitung 1×16 mm²", "Кабель уравнивания потенциалов 1×16 мм²", "potential", "1.5", "55"),
    ("control-7x1-5", "Steuerleitung 7×1,5 mm²", "Управляющий кабель 7×1,5 мм²", "control", "1.5", "55"),
    ("power-5x10", "Leistungskabel 5×10 mm²", "Силовой кабель 5×10 мм²", "power", "2", "70"),
    ("power-5x16", "Leistungskabel 5×16 mm²", "Силовой кабель 5×16 мм²", "power", "2", "70"),
    ("power-5x25", "Leistungskabel 5×25 mm²", "Силовой кабель 5×25 мм²", "power", "2", "70"),
    ("power-5x35", "Leistungskabel 5×35 mm²", "Силовой кабель 5×35 мм²", "heavy", "3", "100"),
    ("power-5x50", "Leistungskabel 5×50 mm²", "Силовой кабель 5×50 мм²", "heavy", "3", "100"),
]

ROUTES = [
    ("wr-uv", "Wechselrichter → UV-PV", "Инвертор → UV-PV"),
    ("uv-nh-new", "UV-PV → neuer NH-Verteiler", "UV-PV → новый NH-распределитель"),
    ("nh-new-hv", "Neuer NH-Verteiler → HV", "Новый NH-распределитель → HV"),
    ("uv-hv", "UV-PV → HV", "UV-PV → HV"),
    ("hpas-new-old", "Neue HPAS → vorhandene HPAS", "Новая HPAS → существующая HPAS"),
    ("uv-key-switch", "UV-PV → Schlüsselschalter", "UV-PV → ключевой выключатель"),
    ("other", "Sonstiger Weg", "Другой путь"),
]


def seed(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    CableType = apps.get_model("work_catalog", "CableType")
    CableRoute = apps.get_model("work_catalog", "CableRoute")
    alias = schema_editor.connection.alias
    active_codes = {row[0] for row in WORKS}
    WorkType.objects.using(alias).filter(direction="ac").exclude(code__in=active_codes).update(is_active=False)
    for order, row in enumerate(WORKS):
        code, de, ru, unit, rule, price_mode, norm, price, construction, is_break = row
        WorkType.objects.using(alias).update_or_create(
            code=code,
            defaults={
                "name_de": de,
                "name_ru": ru,
                "direction": "ac",
                "unit": unit,
                "calculation_rule": rule,
                "price_mode": price_mode,
                "normative_hours": Decimal(norm),
                "unit_price": Decimal(price),
                "underconstruction_hours": Decimal(construction),
                "is_break": is_break,
                "is_active": True,
                "sort_order": order,
            },
        )
    for order, (code, de, ru, category, norm, price) in enumerate(CABLES):
        CableType.objects.using(alias).update_or_create(
            code=code,
            defaults={
                "name_de": de,
                "name_ru": ru,
                "category": category,
                "normative_hours_per_ten_meters": Decimal(norm),
                "unit_price_per_ten_meters": Decimal(price),
                "is_active": True,
                "sort_order": order,
            },
        )
    for order, (code, de, ru) in enumerate(ROUTES):
        CableRoute.objects.using(alias).update_or_create(
            code=code,
            defaults={"name_de": de, "name_ru": ru, "is_active": True, "sort_order": order},
        )


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0006_cabletype_unit_price_per_ten_meters")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
