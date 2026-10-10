"""Начальный согласованный каталог MBG."""

from django.db import migrations

ITEMS = [
    ["nh-montage", "Montage NH-Verteiler", "Монтаж NH-распределителя"],
    ["uv-montage", "Montage UV-PV", "Монтаж щита UV-PV"],
    ["wr-montage", "Montage Wechselrichter", "Монтаж инвертора"],
    ["komm-montage", "Montage Kommbox", "Монтаж коммуникационного блока"],
    ["erder", "Errichten eines Tiefenerders", "Устройство глубинного заземлителя"],
    ["potential", "Herstellen des Potentialausgleichs", "Устройство уравнивания потенциалов"],
    ["hv-nh", "Kabelverlegung von HV zu NH-Verteiler", "Прокладка кабеля от HV до NH"],
    ["nh-uv", "Kabelverlegung von NH-Verteiler zu UV-PV", "Прокладка кабеля от NH до UV-PV"],
    ["uv-wr", "Kabelverlegung von UV-PV zu WR", "Прокладка кабеля от UV-PV до инвертора"],
    ["komm-kabel", "Kabelverlegung Kommunikation", "Прокладка коммуникационного кабеля"],
    [
        "licht",
        "Umsetzen vorhandener Beleuchtung für die Kabeltrasse",
        "Перенос существующего освещения для кабельной трассы",
    ],
    ["material", "Materialabholung und Materialtransport zum Standort", "Забор и доставка материала на объект"],  # noqa: RUF001
    ["wr-anschluss", "Anschluss Wechselrichter", "Подключение инвертора"],
    ["uv-anschluss", "Anschluss UV-PV", "Подключение UV-PV"],
    ["nh-anschluss", "Anschluss NH-Verteiler", "Подключение NH-распределителя"],
    ["komm-anschluss", "Anschluss Kommbox", "Подключение коммуникационного блока"],
]


def seed(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    for index, (code, de, ru) in enumerate(ITEMS):
        WorkType.objects.using(schema_editor.connection.alias).get_or_create(
            code=code, defaults={"name_de": de, "name_ru": ru, "direction": "ac", "sort_order": index}
        )


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
