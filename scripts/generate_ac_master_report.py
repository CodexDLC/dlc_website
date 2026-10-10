"""CLI-скрипт генерации единого сводного отчёта по всем объектам AC (KW36 - KW40).

Тонкий адаптер, потребляющий единый генератор master_workbook:
- Нулевые ставки и цены на новые работы;
- Сохранение фактических часов и физических объёмов;
- Лист 1: Übersicht с выпадающим списком оплаты (Bezahlt / Offen);
- Листы объектов: персональные листы по каждому объекту.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "dlc_montage"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlc_montage.core.settings.dev")

import django

django.setup()

import openpyxl  # noqa: F401
from features.mbg_reports.master_workbook import build_master_settlement_workbook


def main():
    wb = build_master_settlement_workbook()

    output_dir = r"d:\Workspace\clients\dlc_montage\media\exports"
    os.makedirs(output_dir, exist_ok=True)
    filename = "DLC_Montage_AC_Gesamtabrechnung_KW36-KW40.xlsx"
    filepath = os.path.join(output_dir, filename)
    wb.save(filepath)
    print(f"Excel-Report successfully saved to: {filepath}")

    outputs_dir = r"d:\Workspace\clients\dlc_montage\outputs"
    os.makedirs(outputs_dir, exist_ok=True)
    outputs_filepath = os.path.join(outputs_dir, filename)
    wb.save(outputs_filepath)
    print(f"Backup copy saved to: {outputs_filepath}")


if __name__ == "__main__":
    main()
