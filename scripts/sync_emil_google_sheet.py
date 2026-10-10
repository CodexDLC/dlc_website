# ruff: noqa: RUF001, E501
"""Скрипт синхронизации отчёта приёмки куратора (Эмиль) с Google Таблицей.

Возможности:
1. Подключается к Google Таблице по Service Account.
2. Сохраняет существующие ручные пометки куратора (Abnahme-Status, Bemerkung, Freigabe).
3. Обновляет сводный лист «Übersicht Abnahme».
4. Обновляет персональные листы Standorte с 7-колоночной таблицей:
   «Pos.», «Leistung», «Einheit», «Menge», «Status Montage (DLC)», «Abnahme (Bauleiter Emil)», «Bemerkung / Mangel (Emil)»
   и пустыми полями для ввода замечаний.
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

from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset
from features.mbg_reports.sheet_titles import assign_site_sheet_titles, match_existing_worksheet
from features.projects.models import AcObject


def get_google_client():
    import gspread

    cred_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", r"data/private/dlc-montage-6a848008b8ed.json")
    if not os.path.isabs(cred_file):
        cred_file = str(REPO_ROOT / cred_file)
    return gspread.service_account(filename=cred_file)


def get_spreadsheet(sheet_id=None):
    gc = get_google_client()
    target_id = sheet_id or os.getenv("GOOGLE_EMIL_SHEET_ID") or os.getenv("GOOGLE_SHEET_ID")
    if not target_id:
        raise ValueError("GOOGLE_EMIL_SHEET_ID is not configured in .env")
    return gc.open_by_key(target_id)


def read_existing_curator_notes(ws, known_periods=None):
    """Считывает вручную внесённые куратором статусы и замечания: (iso_year, iso_week, site_name) -> dict.

    При ошибке чтения скрипт ОБЯЗАН упасть до выполнения любой записи!
    Если заголовок недели старый/без указания года, разрешает год только при однозначности из known_periods;
    если неоднозначно — выбрасывает RuntimeError до выполнения записи.
    """
    notes = {}
    try:
        all_vals = ws.get_all_values()
    except Exception as exc:
        print(f"Error: Could not read existing curator notes from sheet: {exc}")
        raise

    current_period = None
    for row in all_vals:
        if not row:
            continue
        first_cell = row[0].strip() if len(row) > 0 else ""
        if first_cell.startswith("KW "):
            match = re.search(r"KW\s*(\d+)", first_cell)
            if match:
                kw = int(match.group(1))
                year_match = re.search(r"\b(20\d\d)\b", first_cell)
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
                                f"Ambiguous period header '{first_cell}' without year: "
                                f"matches multiple or no known years: {unique_years}"
                            )
                    else:
                        raise RuntimeError(
                            f"Ambiguous period header '{first_cell}' without year and no known_periods provided."
                        )
            continue
        if first_cell.isdigit() and len(row) >= 9 and current_period:
            site_name = row[1].strip()
            status_val = row[5].strip() if len(row) > 5 else ""
            note_val = row[6].strip() if len(row) > 6 else ""
            freigabe_val = row[7].strip() if len(row) > 7 else ""
            datum_val = row[8].strip() if len(row) > 8 else ""
            notes[(current_period[0], current_period[1], site_name)] = {
                "status": status_val,
                "note": note_val,
                "freigabe": freigabe_val,
                "datum": datum_val,
            }
    return notes


def merge_or_preserve_site_protocol(existing_rows, new_section1_rows, is_in_prog=False):
    """Объединяет обновлённую секцию 1 (выполненные работы) с существующей секцией 2 (протокол приёмки).

    Сохраняет:
    1. Ручные отметки куратора в Секции 1 (колонки F: Abnahme и G: Bemerkung/Mangel)
       по стабильному идентификатору (Leistung/Name, Einheit).
       Если аннотированная позиция отсутствует в новых данных или дублируется — выбрасывает RuntimeError до записи.
    2. Все строки Секции 2 (вердикт, критерии, список замечаний, подпись).
    Если лист новый или Секции 2 нет, генерирует дефолтный шаблон без выдуманных дефектов и дат.
    """
    sec2_idx = None
    existing_sec1_annotations = {}
    existing_key_counts = {}

    if existing_rows:
        for idx, row in enumerate(existing_rows):
            if not row:
                continue
            if any("2. ABNAHMEPROTOKOLL & MÄNGELRÜGE" in str(cell) for cell in row):
                sec2_idx = idx
                break

            # Parse Section 1 item rows
            first_cell = str(row[0]).strip() if len(row) > 0 else ""
            if first_cell.isdigit() and len(row) >= 3:
                pos_name = str(row[1]).strip()
                pos_unit = str(row[2]).strip()
                key = (pos_name, pos_unit)
                existing_key_counts[key] = existing_key_counts.get(key, 0) + 1

                abnahme_val = str(row[5]).strip() if len(row) > 5 else ""
                bemerkung_val = str(row[6]).strip() if len(row) > 6 else ""
                is_annotated = (abnahme_val != "" and abnahme_val != "—") or (bemerkung_val != "")

                if is_annotated:
                    existing_sec1_annotations[key] = (abnahme_val, bemerkung_val)

    for key in existing_sec1_annotations:
        if existing_key_counts[key] != 1:
            raise RuntimeError(f"Duplicated annotated position '{key[0]}' ({key[1]}) in existing sheet.")

    # Validate that all annotated positions exist in new_section1_rows
    new_key_counts = {}
    for row in new_section1_rows:
        if not row:
            continue
        first_cell = str(row[0]).strip() if len(row) > 0 else ""
        if (isinstance(row[0], int) or first_cell.isdigit()) and len(row) >= 3:
            pos_name = str(row[1]).strip()
            pos_unit = str(row[2]).strip()
            key = (pos_name, pos_unit)
            new_key_counts[key] = new_key_counts.get(key, 0) + 1

    for annotated_key in existing_sec1_annotations:
        if annotated_key not in new_key_counts:
            raise RuntimeError(
                f"Annotated position '{annotated_key[0]}' ({annotated_key[1]}) missing from new positions."
            )
        if new_key_counts[annotated_key] != 1:
            raise RuntimeError(f"Duplicated annotated position '{annotated_key[0]}' in new positions.")

    # Merge annotations into new Section 1
    result = []
    for row in new_section1_rows:
        row_copy = list(row)
        if row_copy:
            first_cell = str(row_copy[0]).strip()
            if (isinstance(row_copy[0], int) or first_cell.isdigit()) and len(row_copy) >= 7:
                pos_name = str(row_copy[1]).strip()
                pos_unit = str(row_copy[2]).strip()
                key = (pos_name, pos_unit)
                if key in existing_sec1_annotations:
                    abn, bem = existing_sec1_annotations[key]
                    row_copy[5] = abn
                    row_copy[6] = bem
        result.append(row_copy)

    # Append Section 2
    if sec2_idx is not None and sec2_idx < len(existing_rows):
        result.append([])
        result.extend(existing_rows[sec2_idx:])
    else:
        result.append([])
        result.append(["2. ABNAHMEPROTOKOLL & MÄNGELRÜGE (Ausfüllen durch Bauleiter Emil)"])
        result.append(["Gesamturteil Abnahme:", "In Prüfung", "", "Freigabe zur Auszahlung:", "Nein"])
        result.append([])
        result.append(
            [
                "Prüfkriterien:",
                "☐ Fotodokumentation vollständig eingereicht",
                "",
                "",
                "☐ Messprotokoll / Schutzleiterprüfung erfolgt",
            ]
        )
        result.append(
            ["", "☐ Kabelwege & Trassenführung nach Vorgabe", "", "", "☐ Baustelle besenrein & Abfälle geräumt"]
        )
        result.append([])
        result.append(["Mängelliste / Korrekturbedarf / Anmerkungen des Bauleiters:"])
        for m_i in range(1, 5):
            result.append([f"{m_i}.", ""])
        result.append([])
        result.append(["Geprüft durch Bauleiter: Emil (SPIE)", "", "", "", "Datum der Abnahme: "])

    return result


def sync_emil_sheet(target_weeks=None, sheet_id=None):
    sh = get_spreadsheet(sheet_id)
    print(f"Connected to Google Spreadsheet: '{sh.title}'")

    try:
        ws_summary = sh.worksheet("Übersicht Abnahme")
    except Exception:
        ws_summary = sh.add_worksheet(title="Übersicht Abnahme", rows=100, cols=12)

    target_weeks_list = list(target_weeks) if target_weeks is not None else None
    dataset = load_accepted_reports_dataset(target_weeks=target_weeks_list)
    existing_notes = read_existing_curator_notes(ws_summary, known_periods=dataset.periods)
    print(f"Found {len(existing_notes)} existing curator entries in sheet.")

    selected_site_ids = set(dataset.all_sites.keys())
    site_obj_map = {sid: AcObject.objects.get(pk=sid) for sid in selected_site_ids}

    # PRE-READ AND VALIDATE ALL RELEVANT EXISTING SHEETS BEFORE ANY WRITE!
    site_sheet_names = assign_site_sheet_titles(
        ((s_id, site_obj_map[s_id].name) for s_id in selected_site_ids), reserved={"Übersicht Abnahme"}
    )
    existing_sheets = sh.worksheets()

    planned_site_updates = []

    for s_id in sorted(selected_site_ids, key=lambda sid: site_obj_map[sid].name):
        site = site_obj_map[s_id]
        s_summary = dataset.all_sites[s_id]
        clean_title = site_sheet_names[s_id]
        ws_obj = match_existing_worksheet(existing_sheets, clean_title, site.name)

        site_periods = sorted(list(set((d.iso_year, d.iso_week) for d in s_summary.day_facts)))
        kw_display = ", ".join(f"KW {k} ({y})" if y != 2026 else f"KW {k}" for (y, k) in site_periods)
        is_in_prog = not s_summary.is_completed

        summary_id = ws_summary.id
        full_url = f"https://docs.google.com/spreadsheets/d/{sh.id}/edit#gid={summary_id}"
        obj_rows = []
        obj_rows.append(
            [
                f"DLC Montage · Abnahmeprotokoll Standort: {s_summary.site_name}",
                "",
                "",
                "",
                "",
                f'=HYPERLINK("{full_url}"; "← Zurück zur Übersicht")',
                "",
            ]
        )
        obj_rows.append(
            [
                f"Standort: {s_summary.site_name}",
                "",
                "",
                "",
                f"Anlage (Gruppe): {s_summary.group_name or '—'}",
                "",
                "",
            ]
        )
        obj_rows.append(
            [
                f"Adresse: {s_summary.address or '—'}",
                "",
                "",
                "",
                f"Bau-Status (DLC): {'In Bearbeitung' if is_in_prog else 'Vollständig abgeschlossen'}",
                "",
                "",
            ]
        )
        obj_rows.append(
            [
                f"Abrechnungszeitraum: {kw_display}",
                "",
                "",
                "",
                "Prüfender Bauleiter: Emil (SPIE)",
                "",
                "",
            ]
        )
        obj_rows.append([])
        obj_rows.append(["1. ERBRACHTE MONTAGELEISTUNGEN (Zur Abnahme durch den Bauleiter)"])
        obj_rows.append(
            [
                "Pos.",
                "Leistung / Montageposition",
                "Einheit",
                "Menge",
                "Status Montage (DLC)",
                "Abnahme (Bauleiter Emil)",
                "Bemerkung / Mangel (Emil)",
            ]
        )

        perf_rows = s_summary.position_rows
        for p_idx, prow in enumerate(perf_rows, 1):
            qty_val = f"{float(prow.quantity):.2f}".rstrip("0").rstrip(".") if prow.quantity is not None else "—"
            obj_rows.append(
                [
                    p_idx,
                    prow.name,
                    prow.unit or "Stk.",
                    qty_val,
                    "In Ausführung" if is_in_prog else "✓ Erledigt",
                    "—",
                    "",
                ]
            )

        existing_obj_rows = []
        if ws_obj:
            try:
                existing_obj_rows = ws_obj.get_all_values()
            except Exception as exc:
                print(f"Error reading existing sheet '{clean_title}': {exc}")
                raise

        # This will validate Section 1 and Section 2 and raise RuntimeError before any write if invalid!
        final_rows = merge_or_preserve_site_protocol(existing_obj_rows, obj_rows, is_in_prog=is_in_prog)
        planned_site_updates.append((ws_obj, clean_title, final_rows))

    # All validations passed! Now build summary rows
    completed_cnt = sum(1 for sid in selected_site_ids if dataset.all_sites[sid].is_completed)
    in_prog_cnt = len(selected_site_ids) - completed_cnt

    summary_headers = [
        "Nr.",
        "Standort (Objekt)",
        "Adresse",
        "Anlage (Projektgruppe)",
        "Bau-Status (DLC)",
        "Abnahme-Status (Emil)",
        "Prüfnotiz / Bemerkung des Bauleiters",
        "Freigabe",
        "Prüfdatum",
    ]

    week_titles = {
        (2026, 39): "KW 39 (21.09.2026 – 25.09.2026)",
        (2026, 40): "KW 40 (28.09.2026 – 02.10.2026)",
    }

    summary_rows = []
    summary_rows.append(
        [
            "DLC Montage · Abnahme & Leistungsfreigabe (Bauleitung)",
            "",
            "",
            "",
            "",
            "Auftragnehmer: DLC Montage (Mikhail)",
            "Bauleitung / Abnahme: Emil (SPIE)",
        ]
    )
    summary_rows.append(
        [
            "Prüfprotokoll und Freigabeübersicht der fertiggestellten Montageleistungen",
            "",
            "",
            "",
            "",
            "Projekt: AC-Montage Berlin",
            "",
        ]
    )
    summary_rows.append([])
    summary_rows.append(["★ Prüfübersicht zur Freigabe"])
    summary_rows.append(
        [
            f"Geprüfte Standorte im Zeitraum: {len(selected_site_ids)} gesamt  |  "
            f"Montage abgeschlossen: {completed_cnt}  |  "
            f"In Bearbeitung: {in_prog_cnt}  |  "
            f"Freigabe zur Abrechnung durch Bauleitung (Emil)"
        ]
    )
    summary_rows.append([])

    for iso_year, iso_week in dataset.periods:
        sites_in_period = dataset.sites_by_period.get((iso_year, iso_week), {})
        if not sites_in_period:
            continue

        p_title = week_titles.get((iso_year, iso_week), f"KW {iso_week} / {iso_year}")
        summary_rows.append([p_title])
        summary_rows.append(summary_headers)

        sorted_sites = sorted(sites_in_period.items(), key=lambda x: x[1].site_name)
        for idx, (_s_id, s_summary) in enumerate(sorted_sites, 1):
            status_text = s_summary.construction_status

            saved = existing_notes.get((iso_year, iso_week, s_summary.site_name), {})
            status_val = saved.get("status") or s_summary.curator_review.status
            note_val = saved.get("note") if saved.get("note") is not None else s_summary.curator_review.note
            freigabe_val = saved.get("freigabe") or s_summary.curator_review.freigabe
            datum_val = saved.get("datum") or s_summary.curator_review.date

            summary_rows.append(
                [
                    idx,
                    s_summary.site_name,
                    s_summary.address or "—",
                    s_summary.group_name or "—",
                    status_text,
                    status_val,
                    note_val,
                    freigabe_val,
                    datum_val,
                ]
            )
        summary_rows.append([])

    # NOW perform the writes
    print(f"Updating 'Übersicht Abnahme' with {len(summary_rows)} rows...")
    ws_summary.update(range_name=f"A1:I{len(summary_rows)}", values=summary_rows)
    print("Google Sheet 'Übersicht Abnahme' updated successfully!")

    for ws_obj, clean_title, final_rows in planned_site_updates:
        if ws_obj:
            print(f"Updating '{clean_title}' with {len(final_rows)} rows...")
            ws_obj.update(range_name=f"A1:G{len(final_rows)}", values=final_rows, value_input_option="USER_ENTERED")
        else:
            print(f"Creating worksheet '{clean_title}' with {len(final_rows)} rows...")
            new_ws = sh.add_worksheet(title=clean_title, rows=len(final_rows) + 20, cols=10)
            new_ws.update(range_name=f"A1:G{len(final_rows)}", values=final_rows, value_input_option="USER_ENTERED")

    print("\nAll site worksheets updated in Google Sheets!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet-id", help="Google Sheet ID for Emil")
    args = parser.parse_args()
    sync_emil_sheet(sheet_id=args.sheet_id)
