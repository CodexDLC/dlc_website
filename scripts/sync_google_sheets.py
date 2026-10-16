# ruff: noqa: RUF001, RUF002
"""Скрипт синхронизации данных DLC Montage с Google Таблицей.

Возможности:
1. Подключается к Google Таблице по Service Account.
2. Считывает текущие отметки об оплате ("Bezahlt" / "Offen"), сделанные вручную в Google Таблице,
   чтобы НЕ перезаписывать ручные изменения пользователя/шефа.
3. Считывает актуальные данные из базы dlc_montage (новые недели, часы, позиции, мастера).
4. Обновляет сводный лист «Übersicht» и персональные листы объектов (Standorte).
5. Также актуализирует локальный файл Excel в media/exports/.
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
DLC_DIR = SRC_DIR / "dlc_montage"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(DLC_DIR) not in sys.path:
    sys.path.insert(0, str(DLC_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlc_montage.core.settings.dev")

import django

django.setup()

from features.mbg_reports.google_sync import pad_generated_summary_rows, read_existing_summary_values
from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset
from features.mbg_reports.settlement_scope import project_settlement_dataset
from features.projects.models import AcObject
from sheet_titles import assign_site_sheet_titles, match_existing_worksheet

GERMAN_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def get_google_client():
    import gspread

    cred_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", r"data/private/dlc-montage-6a848008b8ed.json")
    if not os.path.isabs(cred_file):
        cred_file = str(REPO_ROOT / cred_file)
    return gspread.service_account(filename=cred_file)


def get_spreadsheet():
    sheet_id = os.getenv('GOOGLE_SHEET_ID', "").strip()
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID must be configured explicitly before Google Sheets access.")
    gc = get_google_client()
    return gc.open_by_key(sheet_id)


def read_existing_payments(ws_summary, known_periods=None, *, existing_values=None):
    """Считать текущие статусы оплаты из Google Sheets, чтобы не затереть их.

    Возвращает словарь: (iso_year, iso_week, site_name) -> "Bezahlt" | "Offen".
    При любой ошибке чтения скрипт ОБЯЗАН прерываться до выполнения какой-либо записи!
    Если заголовок недели старый/без указания года, разрешает год только при однозначности из known_periods;
    если неоднозначно — выбрасывает RuntimeError до выполнения записи.
    """
    payments = {}
    all_vals = read_existing_summary_values(ws_summary) if existing_values is None else existing_values

    current_period = None
    for row in all_vals:
        if not row:
            continue
        first_col = row[0].strip() if len(row) > 0 else ""
        if first_col.startswith("KW ") and (
            "–" in first_col or "/" in first_col or "(" in first_col or len(first_col.split()) <= 3
        ):
            kw_match = re.search(r"KW\s*(\d+)", first_col)
            if kw_match:
                kw = int(kw_match.group(1))
                year_match = re.search(r"\b(20\d\d)\b", first_col)
                if year_match:
                    current_period = (int(year_match.group(1)), kw)
                else:
                    if known_periods:
                        matching_years = [y for (y, k) in known_periods if k == kw]
                        unique_years = list(set(matching_years))
                        if len(unique_years) == 1:
                            current_period = (unique_years[0], kw)
                        else:
                            raise RuntimeError(
                                f"Ambiguous period header '{first_col}' without year: "
                                f"matches multiple or no known years: {unique_years}"
                            )
                    else:
                        raise RuntimeError(
                            f"Ambiguous period header '{first_col}' without year and no known_periods provided."
                        )
            continue
        if len(row) >= 10 and current_period and row[1]:
            site_name = row[1].strip()
            pay_val = row[9].strip()
            if pay_val in ("Bezahlt", "Offen"):
                payments[(current_period[0], current_period[1], site_name)] = pay_val
    return payments


def sync_all(target_weeks=None):
    sh = get_spreadsheet()
    print(f"Connected to Google Spreadsheet: '{sh.title}'")

    ws_summary = sh.worksheet("Übersicht")

    # Собираем актуальные данные через единый контракт принятых отчётов
    dataset = project_settlement_dataset(
        load_accepted_reports_dataset(target_weeks=list(target_weeks) if target_weeks else None)
    )
    existing_values = read_existing_summary_values(ws_summary)
    existing_payments = read_existing_payments(
        ws_summary, known_periods=dataset.periods, existing_values=existing_values
    )
    print(f"Found {len(existing_payments)} existing payment status entries in sheet.")

    all_sites_set = set(dataset.all_sites.keys())
    site_obj_map = {sid: AcObject.objects.get(pk=sid) for sid in all_sites_set}

    site_sheet_names = assign_site_sheet_titles(
        ((site_id, site.name) for site_id, site in site_obj_map.items()), reserved={"Übersicht"}
    )
    worksheets = sh.worksheets()
    for site_id, title in site_sheet_names.items():
        match_existing_worksheet(worksheets, title, site_obj_map[site_id].name)

    # Статистика KW38+
    kw38_plus_sites = set()
    kw38_plus_hours = 0.0
    kw38_plus_amount = 0.0
    for period, sites_map in dataset.sites_by_period.items():
        if period[0] > 2026 or (period[0] == 2026 and period[1] >= 38):
            for s_id, s_summary in sites_map.items():
                kw38_plus_sites.add(s_id)
                kw38_plus_hours += float(s_summary.total_hours)
                kw38_plus_amount += float(s_summary.total_material_amount)

    completed_count = sum(1 for s_id in kw38_plus_sites if dataset.all_sites[s_id].is_completed)
    in_progress_count = len(kw38_plus_sites) - completed_count
    in_prog_names = ", ".join(
        sorted(
            dataset.all_sites[s_id].site_name for s_id in kw38_plus_sites if not dataset.all_sites[s_id].is_completed
        )
    )
    in_prog_suffix = f" ({in_prog_names})" if in_prog_names else ""

    formatted_kw38_amount = f"{kw38_plus_amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    # Формируем строки для листа Übersicht
    week_names = {
        (2026, 36): "KW 36 (31.08.2026 – 04.09.2026)",
        (2026, 37): "KW 37 (07.09.2026 – 11.09.2026)",
        (2026, 38): "KW 38 (14.09.2026 – 18.09.2026) · [Zur Abrechnung]",
        (2026, 39): "KW 39 (21.09.2026 – 25.09.2026) · [Zur Abrechnung]",
        (2026, 40): "KW 40 (28.09.2026 – 02.10.2026) · [Zur Abrechnung]",
    }

    summary_headers = [
        "Nr.",
        "Standort (Objekt)",
        "Adresse",
        "Anlage (Projektgruppe)",
        "Status",
        "Arbeitstage",
        "Mitarbeiter",
        "Stunden (h)",
        "Betrag (€)",
        "Zahlung",
    ]

    summary_rows = []
    summary_rows.append(
        [
            "DLC Montage · AC Gesamtabrechnung & Leistungsnachweis",
            "",
            "",
            "",
            "",
            "",
            "DLC Montage",
            "Dmitri Labodin",
            "",
        ]
    )
    summary_rows.append(
        [
            "Gesamtübersicht aller AC-Standorte nach Kalenderwochen",
            "",
            "",
            "",
            "",
            "",
            "Tel: +49 176 62203619  ·  dmitri.labodin@googlemail.com",
            "",
            "",
        ]
    )
    summary_rows.append([])
    summary_rows.append(["★ Zur Auszahlung & Abrechnung eingereichte Standorte (ab KW 38)"])
    summary_rows.append(
        [
            f"Im Abrechnungszeitraum (KW 38–40) bearbeitete Standorte: {len(kw38_plus_sites)} gesamt  |  "
            f"Vollständig abgeschlossen: {completed_count}  |  "
            f"In Bearbeitung: {in_progress_count}{in_prog_suffix}  |  "
            f"Gesamtstunden: {kw38_plus_hours:.2f} h  |  "
            f"Materiallogistik (50,00 € pauschal): {formatted_kw38_amount}  |  "
            f"Montagepreise: in Abstimmung (0,00 €)"
        ]
    )
    summary_rows.append([])

    total_all_hours = 0.0
    total_all_amount = 0.0

    for iso_year, iso_week in dataset.periods:
        sites_in_period = dataset.sites_by_period.get((iso_year, iso_week), {})
        if not sites_in_period:
            continue

        p_title = week_names.get((iso_year, iso_week), f"KW {iso_week} / {iso_year}")
        summary_rows.append([p_title])
        summary_rows.append(summary_headers)

        kw_hours = 0.0
        kw_amount = 0.0
        sorted_sites = sorted(sites_in_period.items(), key=lambda x: x[1].site_name)

        for idx, (_s_id, s_summary) in enumerate(sorted_sites, 1):
            status_text = s_summary.construction_status

            work_days = s_summary.work_days_count
            emp_str = ", ".join(s_summary.unique_employee_names) if s_summary.unique_employee_names else "—"

            site_hours = float(s_summary.total_hours)
            site_amount = float(s_summary.total_material_amount)

            kw_hours += site_hours
            kw_amount += site_amount

            # Сохраняем существующий статус оплаты из Google Таблицы
            payment_status = existing_payments.get((iso_year, iso_week, s_summary.site_name), "Offen")

            summary_rows.append(
                [
                    idx,
                    s_summary.site_name,
                    s_summary.address or "—",
                    s_summary.group_name or "—",
                    status_text,
                    work_days,
                    emp_str,
                    f"{site_hours:.2f}",
                    f"{site_amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                    payment_status,
                ]
            )

        # Подитог недели
        summary_rows.append(
            [
                "",
                "",
                "",
                "",
                "",
                "",
                f"Zwischensumme {p_title.split(' · ')[0]}",
                f"{kw_hours:.2f}",
                f"{kw_amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                "",
            ]
        )
        summary_rows.append([])

        total_all_hours += kw_hours
        total_all_amount += kw_amount

    # Итог по всем неделям
    summary_rows.append(
        [
            "",
            "",
            "",
            "",
            "",
            "",
            "Gesamtsumme aller Wochen",
            f"{total_all_hours:.2f}",
            f"{total_all_amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
            "",
        ]
    )

    # Отправляем обновлённый массив строк на лист Übersicht в Google Sheets
    summary_rows = pad_generated_summary_rows(summary_rows, len(existing_values))
    print(f"Updating 'Übersicht' with {len(summary_rows)} rows...")
    ws_summary.update(range_name=f"A1:J{len(summary_rows)}", values=summary_rows)
    print("Google Sheet 'Übersicht' updated successfully!")

    print("\n--- Sync Summary ---")
    print(f"Total Periods in Sheet: {len(dataset.periods)}")
    print(f"Total Objects in Sheet: {len(all_sites_set)}")
    print(f"Total Hours: {total_all_hours:.2f} h")
    print(f"KW 38+ Hours (Auszahlung): {kw38_plus_hours:.2f} h")


if __name__ == "__main__":
    sync_all()
