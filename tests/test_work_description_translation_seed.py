"""Approved seed translations retain physical and electrical details."""

# ruff: noqa: RUF001

from features.work_catalog.description_translations import translate_description


def test_seed_translation_preserves_cable_measurements_and_routes():
    assert translate_description(
        "Kabelverlegung · Wechselrichter 1 → UV-PV · Leistungskabel 5×16 mm²"
    ) == "Прокладка кабеля · инвертор 1 → UV-PV · силовой кабель 5×16 мм²"


def test_seed_translation_preserves_product_names_and_quantity():
    assert translate_description(
        "Anschluss Wechselrichter · 2 Stück (SolarEdge SE25K & SE30K)"
    ) == "Подключение инвертора · 2 шт. (SolarEdge SE25K & SE30K)"


def test_seed_translation_uses_longest_phrase_without_rewriting_its_result():
    assert translate_description(
        "Anschluss an die vorhandene Potentialausgleichsschiene"
    ) == "Подключение к существующей шине уравнивания потенциалов"


def test_seed_translation_rejects_unknown_work_and_private_address():
    assert translate_description("Montage unbekannte Anlage") is None
    assert translate_description("Materialabholung Beispielstraße 7") is None
