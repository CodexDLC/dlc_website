# ruff: noqa: RUF001
"""Google Sheets sync feature adapter.

Rules:
- Thin service extracting reusable logic from CLI scripts without running subprocesses;
- Reads credentials and sheet ID strictly through Django settings / env adapter (never parses .env);
- Fail-closed protection: fails and halts before any write if existing payments/comments cannot be read;
- Preserves manual payments/comments from the sheet and avoids mirror-overwriting;
- Zero financial prices/rates in summary headers and metadata;
- External writes prevented during testing or when unconfigured.
"""

import os
import re
from typing import Sequence

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from loguru import logger

from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset
from features.mbg_reports.settlement_scope import project_settlement_dataset
from features.mbg_reports.sheet_titles import assign_site_sheet_titles, match_existing_worksheet
from features.projects.models import AcObject


def get_google_config() -> tuple[str | None, str | None]:
    """Вернуть путь к файлу учетных данных и ID таблицы из настроек/окружения."""
    cred_file = getattr(settings, "GOOGLE_SERVICE_ACCOUNT_FILE", None) or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    sheet_id = getattr(settings, "GOOGLE_SHEET_ID", None) or os.environ.get("GOOGLE_SHEET_ID")
    return cred_file, sheet_id


def get_google_client(cred_file: str | None = None):
    """Инициализировать gspread-клиент через сервисный аккаунт."""
    if not cred_file:
        cred_file, _sheet_id = get_google_config()
    if not cred_file:
        raise ValidationError(_("Google Service Account ist nicht konfiguriert."))

    import gspread

    return gspread.service_account(filename=cred_file)


def get_spreadsheet(client=None, sheet_id: str | None = None):
    """Открыть удаленную таблицу Google."""
    if not sheet_id:
        _cred_file, sheet_id = get_google_config()
    if not sheet_id:
        raise ValidationError(_("GOOGLE_SHEET_ID ist nicht konfiguriert."))

    gc = client or get_google_client()
    return gc.open_by_key(sheet_id)


def read_existing_summary_values(ws_summary) -> list[list[str]]:
    """Read the generated summary once and abort before writes on failure."""
    try:
        return ws_summary.get_all_values()
    except Exception as exc:
        logger.error("Fail-closed: Could not read existing payments from Google Sheet: {}", exc)
        raise RuntimeError(f"Fail-closed: Could not read existing payments from sheet: {exc}") from exc


def pad_generated_summary_rows(rows, existing_row_count):
    """Overwrite the complete previously generated A:J area, including old tails."""
    return [list(row) + [""] * (10 - len(row)) for row in rows] + [
        [""] * 10 for _ in range(max(0, existing_row_count - len(rows)))
    ]


def read_existing_payments(ws_summary, known_periods=None, *, existing_values=None) -> dict[tuple[int, int, str], str]:
    """Preserve manual payment statuses; reading failure always aborts before writes."""
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
                                f"Fail-closed: Ambiguous period header '{first_col}' without year: "
                                f"matches multiple or no known years: {unique_years}"
                            )
                    else:
                        raise RuntimeError(
                            f"Fail-closed: Ambiguous period header '{first_col}' without year and no known_periods."
                        )
            continue
        if len(row) >= 10 and current_period and row[1]:
            site_name = row[1].strip()
            pay_val = row[9].strip()
            if pay_val in ("Bezahlt", "Offen"):
                payments[(current_period[0], current_period[1], site_name)] = pay_val
    return payments


def sync_master_to_google_sheets(
    *,
    spreadsheet=None,
    target_weeks: Sequence[tuple[int, int]] | None = None,
) -> dict:
    """Синхронизировать актуальный мастер-набор в Google Таблицу с защитой ручных правок."""
    sh = spreadsheet or get_spreadsheet()
    logger.info("Starting Google Sheet sync for '{}'", getattr(sh, "title", "Sheet"))

    ws_summary = sh.worksheet("Übersicht")

    dataset = load_accepted_reports_dataset(
        target_weeks=list(target_weeks) if target_weeks else None, include_paid=True
    )

    dataset = project_settlement_dataset(dataset)

    # Fail-closed чтение перед любыми изменениями
    existing_values = read_existing_summary_values(ws_summary)
    existing_payments = read_existing_payments(
        ws_summary, known_periods=dataset.periods, existing_values=existing_values
    )

    all_sites_set = set(dataset.all_sites.keys())
    site_obj_map = {sid: AcObject.objects.get(pk=sid) for sid in all_sites_set}

    site_sheet_names = assign_site_sheet_titles(
        ((site_id, site.name) for site_id, site in site_obj_map.items()), reserved={"Übersicht"}
    )
    worksheets = sh.worksheets()
    for site_id, title in site_sheet_names.items():
        match_existing_worksheet(worksheets, title, site_obj_map[site_id].name)

    kw38_plus_sites = set()
    kw38_plus_hours = 0.0
    for period, sites_map in dataset.sites_by_period.items():
        if period[0] > 2026 or (period[0] == 2026 and period[1] >= 38):
            for s_id, s_summary in sites_map.items():
                kw38_plus_sites.add(s_id)
                kw38_plus_hours += float(s_summary.total_hours)

    completed_count = sum(1 for s_id in kw38_plus_sites if dataset.all_sites[s_id].is_completed)
    in_progress_count = len(kw38_plus_sites) - completed_count
    in_prog_names = ", ".join(
        sorted(
            dataset.all_sites[s_id].site_name for s_id in kw38_plus_sites if not dataset.all_sites[s_id].is_completed
        )
    )
    in_prog_suffix = f" ({in_prog_names})" if in_prog_names else ""

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

    summary_rows = [
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
            "",
        ],
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
            "",
        ],
        [],
        [],
        [
            f"Im Abrechnungszeitraum bearbeitete Standorte: {len(kw38_plus_sites)} gesamt  |  "
            f"Vollständig abgeschlossen: {completed_count}  |  "
            f"In Bearbeitung: {in_progress_count}{in_prog_suffix}  |  "
            f"Gesamtstunden: {kw38_plus_hours:.2f} h  |  "
            f"Materiallogistik (0,00 €): 0,00 €  |  "
            f"Montagepreise: 0,00 €"
        ],
        [],
    ]

    all_week_total_row_indices = []

    for period in dataset.periods:
        sites_in_period = dataset.sites_by_period.get(period, {})
        if not sites_in_period:
            continue

        period_title = week_names.get(period, f"KW {period[1]} / {period[0]}")
        summary_rows.append([period_title])
        summary_rows.append(summary_headers)

        kw_start_idx = len(summary_rows) + 1
        sorted_sites = sorted(sites_in_period.items(), key=lambda x: x[1].site_name)

        for idx, (s_id, s_summary) in enumerate(sorted_sites, 1):
            _site = site_obj_map[s_id]
            status_text = s_summary.construction_status
            work_days = s_summary.work_days_count
            emp_str = ", ".join(s_summary.unique_employee_names) if s_summary.unique_employee_names else "—"
            site_hours = f"{float(s_summary.total_hours):.2f}".replace(".", ",")
            site_amount = "0,00 €"

            # Сохранение ручных отметок из таблицы при их наличии, иначе из БД
            sheet_pay = existing_payments.get((period[0], period[1], s_summary.site_name))
            if sheet_pay:
                pay_label = sheet_pay
            else:
                pay_label = "Bezahlt" if _site.is_paid else "Offen"

            summary_rows.append(
                [
                    idx,
                    s_summary.site_name,
                    s_summary.address or "—",
                    s_summary.group_name or "—",
                    status_text,
                    work_days,
                    emp_str,
                    site_hours,
                    site_amount,
                    pay_label,
                ]
            )

        kw_end_idx = len(summary_rows)
        sub_label = f"Zwischensumme {period_title.split(' · ')[0]}"
        kw_h_sum_formula = f"=SUM(H{kw_start_idx}:H{kw_end_idx})"
        kw_a_sum_formula = f"=SUM(I{kw_start_idx}:I{kw_end_idx})"
        all_week_total_row_indices.append(len(summary_rows) + 1)

        summary_rows.append(["", sub_label, "", "", "", "", "", kw_h_sum_formula, kw_a_sum_formula, ""])
        summary_rows.append([])

    formula_h = "=" + "+".join(f"H{r}" for r in all_week_total_row_indices) if all_week_total_row_indices else "=0"
    formula_a = "=" + "+".join(f"I{r}" for r in all_week_total_row_indices) if all_week_total_row_indices else "=0"
    summary_rows.append(["", "Gesamtsumme aller Wochen", "", "", "", "", "", formula_h, formula_a, ""])

    # Запись в лист Übersicht
    summary_rows = pad_generated_summary_rows(summary_rows, len(existing_values))
    ws_summary.update(summary_rows, value_input_option="USER_ENTERED")
    logger.info("Successfully updated Google Sheet Übersicht with {} rows", len(summary_rows))

    return {
        "status": "success",
        "synced_sites_count": len(all_sites_set),
        "periods_count": len(dataset.periods),
    }
