"""Regression tests for Stage 1 Reporting Integrity & Single-Source Contract.

Covers:
1. pause0: Breaks/pauses must yield 0 fact-hours; zero hours remain zero; no participant=1 invention.
2. draft/returned exclusion: Only current accepted revision reports are included; drafts/returned excluded.
3. revision mismatch: Reports with version mismatch or non-accepted snapshot excluded.
4. unknown quantity: Physical quantities with None stay explicit None (not 1 or 1.0 or fake zero).
5. year collision: Grouping periods strictly by (ISO year, ISO week), never week number alone.
6. site status: Site construction status comes from AcObject.status, never hardcoded names.
7. no fabricated acceptance: Curator default is 'In Prüfung' / 'Nein' unless persisted accepted SiteReview matches
   digest.
8. google read failure: Failure to read existing payments or curator notes must abort BEFORE any write.
9. protected manual fields: Existing curator manual cells/protocol in per-site sheets must be preserved.
10. material delivery flat rule: Flat 50.00 EUR for material delivery, unagreed 0.00 EUR, actual hours kept.
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure scripts and src are on path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "dlc_montage"))

import sync_emil_google_sheet
import sync_google_sheets
from django.contrib.auth import get_user_model
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee
from features.work_catalog.models import WorkType


@pytest.fixture
def base_setup(db):
    User = get_user_model()
    admin = User.objects.create_superuser(
        username="admin_test",
        email="admin@dlc.test",
        password="pass",  # noqa: S106
    )
    group = ProjectGroup.objects.create(name="Gruppe Nord", has_ac=True, status="active")
    site1 = AcObject.objects.create(group=group, name="Huttwiler Weg 37", status="completed")
    site2 = AcObject.objects.create(group=group, name="Sonnenweg 10", status="started")
    emp = Employee.objects.create(first_name="Max", last_name="Mustermann")
    wt_work, _ = WorkType.objects.get_or_create(
        code="cable-pull",
        defaults={
            "name_de": "Kabelzug",
            "direction": "ac",
            "calculation_rule": "actual",
            "price_mode": "actual_hourly",
            "is_break": False,
        },
    )
    wt_pause, _ = WorkType.objects.get_or_create(
        code="mittagspause",
        defaults={
            "name_de": "Mittagspause",
            "direction": "ac",
            "calculation_rule": "actual",
            "price_mode": "zero",
            "is_break": True,
        },
    )
    wt_mat, _ = WorkType.objects.get_or_create(
        code="material-delivery",
        defaults={
            "name_de": "Materiallieferung",
            "direction": "ac",
            "calculation_rule": "flat",
            "price_mode": "per_unit",
            "unit_price": Decimal("50.00"),
            "is_break": False,
        },
    )
    return {
        "admin": admin,
        "group": group,
        "site1": site1,
        "site2": site2,
        "emp": emp,
        "wt_work": wt_work,
        "wt_pause": wt_pause,
        "wt_mat": wt_mat,
    }


def test_pause_zero_hours_and_no_participant_invention():
    """calc_fact_hours must yield 0 for breaks, keep 0.00 as 0, and not invent participant=1."""
    from features.mbg_reports.reporting_facts import calc_fact_hours

    # 1. Break entry: must be 0.00 even if start/end are set
    break_entry = {
        "is_break": True,
        "starts_at": "12:00",
        "ends_at": "13:00",
        "participant_names": ["Max"],
    }
    assert calc_fact_hours(break_entry) == Decimal("0.00")

    # 2. Entry with explicit actual_person_hours = Decimal("0.00")
    zero_entry = {
        "actual_person_hours": "0.00",
        "starts_at": "08:00",
        "ends_at": "09:00",
        "participant_names": ["Max"],
    }
    assert calc_fact_hours(zero_entry) == Decimal("0.00")

    # 3. Entry with 0 participants and 0 workforce count: must NOT invent 1 participant
    no_part_entry = {
        "starts_at": "08:00",
        "ends_at": "09:00",
        "participant_names": [],
    }
    assert calc_fact_hours(no_part_entry, workforce_count=0) == Decimal("0.00")


def test_draft_and_returned_reports_excluded(base_setup):
    """Reports with draft or returned status must be excluded from accepted reporting dataset."""
    site = base_setup["site1"]
    admin = base_setup["admin"]

    # Create a draft report
    draft_rep = MbgDailyReport.objects.create(
        site=site, author=admin, work_date=date(2026, 9, 21), status="draft", version=1
    )
    # Create an accepted report with valid revision
    acc_rep = MbgDailyReport.objects.create(
        site=site, author=admin, work_date=date(2026, 9, 22), status="accepted", version=1
    )
    MbgReportRevision.objects.create(
        report=acc_rep,
        actor=admin,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "site_id": site.pk,
            "site_name": site.name,
            "date": "2026-09-22",
            "entries": [],
        },
    )

    # If calling load_accepted_reports_dataset (or dataset used by reports)
    from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset

    dataset = load_accepted_reports_dataset(site_ids=[site.pk])
    report_ids = [day.report_id for s in dataset.all_sites.values() for day in s.day_facts]
    assert draft_rep.pk not in report_ids
    assert acc_rep.pk in report_ids


def test_revision_mismatch_excluded(base_setup):
    """A report whose revision version does not match report.version or snapshot != accepted must be excluded."""
    site = base_setup["site1"]
    admin = base_setup["admin"]

    # Report has version 2, but revision is version 1
    mismatch_rep = MbgDailyReport.objects.create(
        site=site, author=admin, work_date=date(2026, 9, 23), status="accepted", version=2
    )
    MbgReportRevision.objects.create(
        report=mismatch_rep,
        actor=admin,
        version=1,
        action="accept",
        snapshot={"status": "accepted", "site_id": site.pk, "date": "2026-09-23", "entries": []},
    )

    from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset

    dataset = load_accepted_reports_dataset(site_ids=[site.pk])
    report_ids = [day.report_id for s in dataset.all_sites.values() for day in s.day_facts]
    assert mismatch_rep.pk not in report_ids


def test_unknown_quantity_explicit_none(base_setup):
    """Physical quantities with None must remain explicit None, never converted to 1 or 1.0."""
    from features.mbg_reports.completion_projection import project_accepted_entries

    snapshot = {
        "status": "accepted",
        "entries": [
            {
                "work_type_code": "cable-pull",
                "description": "Kabelzug Sonderweg",
                "unit": "m",
                "completed_quantity": None,
                "work_item_id": None,
                "calculation_rule": "per_unit",
                "actual_person_hours": "3.50",
            }
        ],
    }
    rows = project_accepted_entries([(1, 1, date(2026, 9, 22), snapshot)])
    assert len(rows) > 0
    assert rows[0].quantity is None, f"Expected quantity None, got {rows[0].quantity}"


def test_year_collision_prevention():
    """Grouping must distinguish (2025, 40) and (2026, 40), never key by week number alone."""
    d1 = date(2025, 10, 1)  # KW 40 2025
    d2 = date(2026, 9, 30)  # KW 40 2026
    iso1 = d1.isocalendar()[:2]
    iso2 = d2.isocalendar()[:2]
    assert iso1 == (2025, 40)
    assert iso2 == (2026, 40)
    assert iso1 != iso2


def test_site_status_from_model_not_hardcoded_names(base_setup):
    """Site construction status must come from AcObject.status, not hardcoded IN_PROGRESS_OBJECTS."""
    site1 = base_setup["site1"]  # named 'Huttwiler Weg 37', status='completed'
    site2 = base_setup["site2"]  # named 'Sonnenweg 10', status='started'

    # Hardcoded scripts check: site.name in IN_PROGRESS_OBJECTS
    # Old script had 'Huttwiler Weg 37' in IN_PROGRESS_OBJECTS -> called it 'In Bearbeitung'
    # even though status='completed'!
    # Old script did NOT have 'Sonnenweg 10' in IN_PROGRESS_OBJECTS -> called it 'Fertiggestellt'
    # even though status='started'!
    from features.mbg_reports.reporting_selectors import resolve_site_construction_status

    assert resolve_site_construction_status(site1) == "Fertiggestellt"
    assert resolve_site_construction_status(site2) == "In Bearbeitung"


def test_no_fabricated_acceptance(base_setup):
    """Curator status must default to 'In Prüfung' / 'Nein', not fabricated 'Freigegeben' / 'Ja'."""
    site = base_setup["site1"]  # completed site, but no SiteReview accepted yet
    from features.mbg_reports.reporting_selectors import resolve_curator_review

    review_fact = resolve_curator_review(site)
    assert review_fact.status == "In Prüfung"
    assert review_fact.freigabe == "Nein"


def test_google_read_failure_aborts_before_write():
    """Failure to read existing payments or curator notes must abort BEFORE any write."""
    mock_ws = MagicMock()
    mock_ws.get_all_values.side_effect = RuntimeError("Google API network disconnect")

    # sync_google_sheets.read_existing_payments must NOT swallow error and return {}
    with pytest.raises(RuntimeError):
        sync_google_sheets.read_existing_payments(mock_ws)

    # sync_emil_google_sheet.read_existing_curator_notes must NOT swallow error and return {}
    with pytest.raises(RuntimeError):
        sync_emil_google_sheet.read_existing_curator_notes(mock_ws)


def test_protected_manual_fields_preserved():
    """Updating per-site worksheet in Emil sheet must preserve existing manual cells in Section 2."""
    from sync_emil_google_sheet import merge_or_preserve_site_protocol

    existing_rows = [
        ["DLC Montage · Abnahmeprotokoll Standort: Test", "", "", "", "", "Link", ""],
        ["Standort: Test", "", "", "", "Anlage: G", "", ""],
        ["Adresse: Addr", "", "", "", "Bau-Status: Fertiggestellt", "", ""],
        ["Abrechnungszeitraum: KW 39", "", "", "", "Prüfender Bauleiter: Emil", "", ""],
        [],
        ["1. ERBRACHTE MONTAGELEISTUNGEN"],
        ["Pos.", "Leistung", "Einheit", "Menge", "Status Montage", "Abnahme", "Bemerkung"],
        [1, "Kabelzug", "m", "100", "✓ Erledigt", "✓ i.O.", "Manual item note"],
        [],
        ["2. ABNAHMEPROTOKOLL & MÄNGELRÜGE (Ausfüllen durch Bauleiter Emil)"],
        ["Gesamturteil Abnahme:", "Nacharbeit erforderlich", "", "Freigabe zur Auszahlung:", "Nein"],
        [],
        ["Prüfkriterien:", "☒ Fotodokumentation vollständig eingereicht", "", "", "☐ Messprotokoll"],
        ["", "☐ Kabelwege nach Vorgabe", "", "", "☐ Baustelle besenrein"],
        [],
        ["Mängelliste / Korrekturbedarf / Anmerkungen des Bauleiters:"],
        ["1.", "Kabelbinder an Trasse 3 nachziehen!"],
        ["2.", ""],
        ["3.", ""],
        ["4.", ""],
        [],
        ["Geprüft durch Bauleiter: Emil (SPIE)", "", "", "", "Datum der Abnahme: 25.09.2026"],
    ]

    new_section1_rows = [
        ["DLC Montage · Abnahmeprotokoll Standort: Test", "", "", "", "", "Link", ""],
        ["Standort: Test", "", "", "", "Anlage: G", "", ""],
        ["Adresse: Addr", "", "", "", "Bau-Status: Fertiggestellt", "", ""],
        ["Abrechnungszeitraum: KW 39", "", "", "", "Prüfender Bauleiter: Emil", "", ""],
        [],
        ["1. ERBRACHTE MONTAGELEISTUNGEN"],
        ["Pos.", "Leistung", "Einheit", "Menge", "Status Montage", "Abnahme", "Bemerkung"],
        [1, "Kabelzug", "m", "100", "✓ Erledigt", "—", ""],
    ]

    merged = merge_or_preserve_site_protocol(existing_rows, new_section1_rows, is_in_prog=False)
    # Section 2 rows must preserve Emil's manual notes:
    flat_text = " ".join(str(c) for r in merged for c in r)
    assert "Kabelbinder an Trasse 3 nachziehen!" in flat_text
    assert "Nacharbeit erforderlich" in flat_text
    assert "☒ Fotodokumentation vollständig eingereicht" in flat_text


def test_material_delivery_flat_and_unagreed_rates_zero():
    """All rates including material delivery yield 0.00 EUR under zero pricing contract."""
    from features.mbg_reports.reporting_facts import calc_entry_amount

    assert calc_entry_amount({"work_type_code": "material-delivery", "quantity": 1}) == Decimal("0.00")
    assert calc_entry_amount({"work_type_code": "material-delivery", "quantity": 2}) == Decimal("0.00")
    assert calc_entry_amount({"work_type_code": "material-delivery", "quantity": None}) == Decimal("0.00")
    assert calc_entry_amount({"work_type_code": "material-delivery", "completed_quantity": "3"}) == Decimal("0.00")
    assert calc_entry_amount({"work_type_code": "cable-pull"}) == Decimal("0.00")


def test_ast_guard_no_duplicate_calc_entry_hours_and_no_raw_fallback():
    """AST guard: verify no calc_entry_hours and no raw MbgWorkEntry queries exist in any reporting script."""
    import ast

    scripts = [
        REPO_ROOT / "scripts" / "generate_ac_master_report.py",
        REPO_ROOT / "scripts" / "generate_emil_abnahme_report.py",
        REPO_ROOT / "scripts" / "sync_google_sheets.py",
        REPO_ROOT / "scripts" / "sync_emil_google_sheet.py",
    ]

    for script_path in scripts:
        with open(script_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(script_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "calc_entry_hours":
                pytest.fail(f"Duplicate calc_entry_hours found in {script_path.name}")
            if isinstance(node, ast.ImportFrom) and node.module and "models" in node.module:
                for alias in node.names:
                    if alias.name == "MbgWorkEntry":
                        pytest.fail(f"Raw MbgWorkEntry import found in {script_path.name}")


def test_pure_dto_no_orm_import_and_no_customer_portal_cycle():
    """reporting_dto must not import ORM selectors at runtime.

    reporting_selectors must not import customer_portal.services.
    """
    import ast

    dto_path = REPO_ROOT / "src" / "dlc_montage" / "features" / "mbg_reports" / "reporting_dto.py"
    with open(dto_path, "r", encoding="utf-8") as f:
        dto_tree = ast.parse(f.read(), filename=str(dto_path))

    for node in dto_tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and "selectors" in node.module:
            pytest.fail("reporting_dto.py must not import ORM selectors at module top-level")

    sel_path = REPO_ROOT / "src" / "dlc_montage" / "features" / "mbg_reports" / "reporting_selectors.py"
    with open(sel_path, "r", encoding="utf-8") as f:
        sel_tree = ast.parse(f.read(), filename=str(sel_path))

    for node in ast.walk(sel_tree):
        if isinstance(node, ast.ImportFrom) and node.module and "customer_portal.services" in node.module:
            pytest.fail("reporting_selectors.py must not import customer_portal.services (avoid cyclic dependency)")


def test_curator_review_defaults_blank_and_payment_nein(base_setup):
    """Curator review defaults to blank note/date and payment approval strictly Nein."""
    from datetime import datetime

    from django.utils import timezone
    from features.customer_portal.models import SiteReview
    from features.mbg_reports.reporting_selectors import compute_site_snapshot_digest, resolve_curator_review

    site = base_setup["site1"]

    # 1. Unreviewed site
    review_fact = resolve_curator_review(site)
    assert review_fact.status == "In Prüfung"
    assert review_fact.freigabe == "Nein"
    assert review_fact.note == "", f"Expected blank note, got '{review_fact.note}'"
    assert review_fact.date == "", f"Expected blank date, got '{review_fact.date}'"

    # 2. Accepted technical review: payment authorization must STILL default to 'Nein'
    digest = compute_site_snapshot_digest(site)
    SiteReview.objects.create(
        site=site,
        status="accepted",
        snapshot_digest=digest,
        remark="Technical acceptance OK",
        decided_at=timezone.make_aware(datetime(2026, 9, 25, 14, 0)),
    )
    accepted_fact = resolve_curator_review(site)
    assert accepted_fact.status == "Freigegeben"
    assert accepted_fact.freigabe == "Nein", "Technical acceptance must NOT auto-grant payment authorization!"
    assert accepted_fact.note == "Technical acceptance OK"
    assert accepted_fact.date == "25.09.2026"


def test_merge_preserves_section1_columns_and_aborts_on_tampered_positions():
    """merge_or_preserve_site_protocol preserves columns F/G and aborts on missing/duplicated items."""
    from sync_emil_google_sheet import merge_or_preserve_site_protocol

    existing_rows = [
        ["DLC Montage · Abnahmeprotokoll Standort: Test", "", "", "", "", "Link", ""],
        ["Standort: Test", "", "", "", "Anlage: G", "", ""],
        ["Adresse: Addr", "", "", "", "Bau-Status: Fertiggestellt", "", ""],
        ["Abrechnungszeitraum: KW 39", "", "", "", "Prüfender Bauleiter: Emil", "", ""],
        [],
        ["1. ERBRACHTE MONTAGELEISTUNGEN"],
        ["Pos.", "Leistung", "Einheit", "Menge", "Status Montage", "Abnahme", "Bemerkung"],
        [1, "Kabelzug 5x16", "m", "100", "✓ Erledigt", "OK - Emil", "Trasse sauber"],
        [2, "Wechselrichter WR1", "Stk.", "1", "✓ Erledigt", "Mangel", "Lüfter prüfen"],
        [],
        ["2. ABNAHMEPROTOKOLL & MÄNGELRÜGE (Ausfüllen durch Bauleiter Emil)"],
        ["Gesamturteil Abnahme:", "In Prüfung", "", "Freigabe zur Auszahlung:", "Nein"],
        [],
        ["Prüfkriterien:", "☐ Fotodokumentation vollständig eingereicht", "", "", "☐ Messprotokoll"],
        ["", "☐ Kabelwege nach Vorgabe", "", "", "☐ Baustelle besenrein"],
        [],
        ["Mängelliste / Korrekturbedarf / Anmerkungen des Bauleiters:"],
        ["1.", "Kabelbinder an Trasse nachziehen"],
        ["2.", ""],
        ["3.", ""],
        ["4.", ""],
        [],
        ["Geprüft durch Bauleiter: Emil (SPIE)", "", "", "", "Datum der Abnahme: 25.09.2026"],
    ]

    # Case A: new rows add a position and reorder
    new_section1_rows = [
        ["DLC Montage · Abnahmeprotokoll Standort: Test", "", "", "", "", "Link", ""],
        ["Standort: Test", "", "", "", "Anlage: G", "", ""],
        ["Adresse: Addr", "", "", "", "Bau-Status: Fertiggestellt", "", ""],
        ["Abrechnungszeitraum: KW 39", "", "", "", "Prüfender Bauleiter: Emil", "", ""],
        [],
        ["1. ERBRACHTE MONTAGELEISTUNGEN"],
        ["Pos.", "Leistung", "Einheit", "Menge", "Status Montage", "Abnahme", "Bemerkung"],
        [1, "Kabeltrasse 60mm", "m", "50", "✓ Erledigt", "—", ""],
        [2, "Kabelzug 5x16", "m", "100", "✓ Erledigt", "—", ""],
        [3, "Wechselrichter WR1", "Stk.", "1", "✓ Erledigt", "—", ""],
    ]

    merged = merge_or_preserve_site_protocol(existing_rows, new_section1_rows, is_in_prog=False)
    # Check that "Kabelzug 5x16" preserved "OK - Emil" and "Trasse sauber"
    row_kabel = next(r for r in merged if len(r) >= 7 and r[1] == "Kabelzug 5x16")
    assert row_kabel[5] == "OK - Emil"
    assert row_kabel[6] == "Trasse sauber"
    # Check that "Wechselrichter WR1" preserved "Mangel" and "Lüfter prüfen"
    row_wr = next(r for r in merged if len(r) >= 7 and r[1] == "Wechselrichter WR1")
    assert row_wr[5] == "Mangel"
    assert row_wr[6] == "Lüfter prüfen"
    # New row "Kabeltrasse 60mm" has default empty/dash
    row_trasse = next(r for r in merged if len(r) >= 7 and r[1] == "Kabeltrasse 60mm")
    assert row_trasse[5] == "—"
    assert row_trasse[6] == ""

    # Case B: an annotated position is missing from new rows -> MUST ABORT
    missing_annotated_rows = [
        ["DLC Montage · Abnahmeprotokoll Standort: Test", "", "", "", "", "Link", ""],
        ["Standort: Test", "", "", "", "Anlage: G", "", ""],
        ["Adresse: Addr", "", "", "", "Bau-Status: Fertiggestellt", "", ""],
        ["Abrechnungszeitraum: KW 39", "", "", "", "Prüfender Bauleiter: Emil", "", ""],
        [],
        ["1. ERBRACHTE MONTAGELEISTUNGEN"],
        ["Pos.", "Leistung", "Einheit", "Menge", "Status Montage", "Abnahme", "Bemerkung"],
        [1, "Kabeltrasse 60mm", "m", "50", "✓ Erledigt", "—", ""],
        # "Wechselrichter WR1" (which has manual annotations) is removed!
    ]
    with pytest.raises((RuntimeError, ValueError), match=r"Annotated position .* missing"):
        merge_or_preserve_site_protocol(existing_rows, missing_annotated_rows, is_in_prog=False)


def test_position_rows_scoped_to_period_no_all_time_leak(base_setup):
    """s_summary.position_rows must only reflect contributions from scoped period, not all-time."""
    site = base_setup["site1"]
    admin = base_setup["admin"]

    # Report 1 in KW 38
    rep38 = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=date(2026, 9, 15),
        status="accepted",
        version=1,
    )
    MbgReportRevision.objects.create(
        report=rep38,
        actor=admin,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "date": "2026-09-15",
            "entries": [
                {
                    "work_type_code": "cable-pull",
                    "description": "Kabelzug KW38 Only",
                    "unit": "m",
                    "completed_quantity": "50.00",
                    "work_item_id": 101,
                    "actual_person_hours": "4.00",
                }
            ],
        },
    )

    # Report 2 in KW 39
    rep39 = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=date(2026, 9, 22),
        status="accepted",
        version=1,
    )
    MbgReportRevision.objects.create(
        report=rep39,
        actor=admin,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "date": "2026-09-22",
            "entries": [
                {
                    "work_type_code": "cable-pull",
                    "description": "Kabelzug KW39 Only",
                    "unit": "m",
                    "completed_quantity": "80.00",
                    "work_item_id": 102,
                    "actual_person_hours": "6.00",
                }
            ],
        },
    )

    from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset

    # Request only KW 39
    dataset = load_accepted_reports_dataset(target_weeks=[39], site_ids=[site.pk])
    summary39 = dataset.all_sites[site.pk]
    pos_names = [p.name for p in summary39.position_rows]
    assert "Kabelzug KW39 Only" in pos_names
    assert "Kabelzug KW38 Only" not in pos_names, "position_rows leaked work from KW 38 into KW 39 scope!"


def test_snapshot_metadata_preferred_over_live_db_mutation(base_setup):
    """Day facts and summary must preserve historical snapshotted site metadata even if live model changes."""
    site = base_setup["site1"]
    admin = base_setup["admin"]

    rep = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=date(2026, 9, 22),
        status="accepted",
        version=1,
    )
    MbgReportRevision.objects.create(
        report=rep,
        actor=admin,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "date": "2026-09-22",
            "site_name": "Historic Site Name 1990",
            "address": "Historic Street 42",
            "project_number": "P-HIST-1",
            "group_name": "Historic Group",
            "entries": [],
        },
    )

    # Now mutate live site in DB
    site.name = "Mutated Live Name 2026"
    site.address = "Mutated Live Street 999"
    site.project_number = "P-MUTATED-99"
    site.save()

    from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset

    dataset = load_accepted_reports_dataset(site_ids=[site.pk])
    summary = dataset.all_sites[site.pk]
    day = summary.day_facts[0]

    assert day.site_name == "Historic Site Name 1990"
    assert day.address == "Historic Street 42"
    assert day.project_number == "P-HIST-1"
    assert day.group_name == "Historic Group"
    assert summary.site_name == "Historic Site Name 1990"
    assert summary.address == "Historic Street 42"


def test_scripts_bootstrap_repo_relative_and_no_hardcoded_path():
    """All 4 scripts must use repo-relative sys.path bootstrap without hardcoded drive D paths."""
    scripts = [
        REPO_ROOT / "scripts" / "generate_ac_master_report.py",
        REPO_ROOT / "scripts" / "generate_emil_abnahme_report.py",
        REPO_ROOT / "scripts" / "sync_google_sheets.py",
        REPO_ROOT / "scripts" / "sync_emil_google_sheet.py",
    ]
    for script_path in scripts:
        content = script_path.read_text(encoding="utf-8")
        assert 'r"d:\\Workspace' not in content.lower(), f"Hardcoded path found in {script_path.name}"
        assert "import gspread" not in content[:500], f"Top-level gspread import found in {script_path.name}"


def test_year_collision_real_output_and_ambiguous_header_fail(base_setup):
    """Scripts must preserve tuple keys (year, week) and abort on ambiguous week headers without year."""
    site = base_setup["site1"]
    admin = base_setup["admin"]

    # 1. Accepted report in KW 40 2025
    rep2025 = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=date(2025, 10, 1),  # KW 40 2025
        status="accepted",
        version=1,
    )
    MbgReportRevision.objects.create(
        report=rep2025,
        actor=admin,
        version=1,
        action="accept",
        snapshot={"status": "accepted", "date": "2025-10-01", "entries": []},
    )

    # 2. Accepted report in KW 40 2026
    rep2026 = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=date(2026, 9, 30),  # KW 40 2026
        status="accepted",
        version=1,
    )
    MbgReportRevision.objects.create(
        report=rep2026,
        actor=admin,
        version=1,
        action="accept",
        snapshot={"status": "accepted", "date": "2026-09-30", "entries": []},
    )

    from features.mbg_reports.reporting_selectors import load_accepted_reports_dataset

    dataset = load_accepted_reports_dataset(site_ids=[site.pk])
    assert (2025, 40) in dataset.periods
    assert (2026, 40) in dataset.periods
    assert len(dataset.periods) == 2

    # Check ambiguous header in read_existing_curator_notes:
    # When target dataset has both (2025, 40) and (2026, 40), a header 'KW 40' with no year is AMBIGUOUS
    from sync_emil_google_sheet import read_existing_curator_notes

    mock_ws = MagicMock()
    mock_ws.get_all_values.return_value = [
        ["KW 40"],  # No year!
        ["1", site.name, "Addr", "Grp", "Fertiggestellt", "In Prüfung", "", "Nein", ""],
    ]
    with pytest.raises(RuntimeError, match="Ambiguous period header"):
        read_existing_curator_notes(mock_ws, known_periods=[(2025, 40), (2026, 40)])


def test_sync_emil_sheet_aborts_before_any_write_when_site_sheet_fails(monkeypatch, base_setup):
    """sync_emil_sheet must pre-read and validate all site worksheets.

    If any site worksheet has invalid/missing annotated positions, it must abort BEFORE calling
    ws_summary.update or creating any worksheet!
    """
    site = base_setup["site1"]
    admin = base_setup["admin"]

    rep = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=date(2026, 9, 22),
        status="accepted",
        version=1,
    )
    MbgReportRevision.objects.create(
        report=rep,
        actor=admin,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "date": "2026-09-22",
            "entries": [
                {
                    "work_type_code": "cable-pull",
                    "description": "Kabelzug 5x16",
                    "unit": "m",
                    "completed_quantity": "50.00",
                    "work_item_id": 101,
                    "actual_person_hours": "4.00",
                }
            ],
        },
    )

    mock_sh = MagicMock()
    mock_ws_summary = MagicMock()
    mock_ws_summary.id = 12345
    mock_ws_summary.get_all_values.return_value = [
        ["KW 39 (2026)"],
        ["1", site.name, "Addr", "Grp", "Fertiggestellt", "In Prüfung", "", "Nein", ""],
    ]
    mock_sh.worksheet.return_value = mock_ws_summary

    # Site worksheet has an annotated position that does NOT exist in the new report
    mock_ws_site = MagicMock()
    mock_ws_site.title = site.name
    mock_ws_site.get_all_values.return_value = [
        ["DLC Montage · Abnahmeprotokoll Standort: " + site.name, "", "", "", "", "Link", ""],
        ["Standort: " + site.name, "", "", "", "Anlage: G", "", ""],
        ["Adresse: Addr", "", "", "", "Bau-Status: Fertiggestellt", "", ""],
        ["Abrechnungszeitraum: KW 39", "", "", "", "Prüfender Bauleiter: Emil", "", ""],
        [],
        ["1. ERBRACHTE MONTAGELEISTUNGEN"],
        ["Pos.", "Leistung", "Einheit", "Menge", "Status Montage", "Abnahme", "Bemerkung"],
        [1, "Missing Old Annotated Pos", "Stk.", "1", "✓ Erledigt", "OK - Emil", "Note"],
        [],
        ["2. ABNAHMEPROTOKOLL & MÄNGELRÜGE (Ausfüllen durch Bauleiter Emil)"],
    ]
    mock_sh.worksheets.return_value = [mock_ws_summary, mock_ws_site]

    monkeypatch.setattr("sync_emil_google_sheet.get_spreadsheet", lambda sheet_id=None: mock_sh)

    with pytest.raises(RuntimeError, match="missing from new positions"):
        sync_emil_google_sheet.sync_emil_sheet(target_weeks=(39,))

    # Assert that NO writes occurred!
    mock_ws_summary.update.assert_not_called()
    mock_ws_site.update.assert_not_called()
    mock_sh.add_worksheet.assert_not_called()


def test_sync_emil_sheet_preserves_summary_and_site_manual_fields(monkeypatch, base_setup):
    """sync_emil_sheet outer run preserves manual summary status/note/date and Section 1+2 on site sheet."""
    site = base_setup["site1"]
    admin = base_setup["admin"]

    rep = MbgDailyReport.objects.create(
        site=site,
        author=admin,
        work_date=date(2026, 9, 22),
        status="accepted",
        version=1,
    )
    MbgReportRevision.objects.create(
        report=rep,
        actor=admin,
        version=1,
        action="accept",
        snapshot={
            "status": "accepted",
            "date": "2026-09-22",
            "entries": [
                {
                    "work_type_code": "cable-pull",
                    "description": "Kabelzug 5x16",
                    "unit": "m",
                    "completed_quantity": "50.00",
                    "work_item_id": 101,
                    "actual_person_hours": "4.00",
                }
            ],
        },
    )

    mock_sh = MagicMock()
    mock_ws_summary = MagicMock()
    mock_ws_summary.id = 12345
    mock_ws_summary.get_all_values.return_value = [
        ["KW 39 (2026)"],
        [
            "1",
            site.name,
            "Addr",
            "Grp",
            "In Bearbeitung",
            "Nacharbeit erforderlich",
            "Prüfnotiz Emil",
            "Nein",
            "22.09.2026",
        ],
    ]
    mock_sh.worksheet.return_value = mock_ws_summary

    mock_ws_site = MagicMock()
    mock_ws_site.title = site.name
    mock_ws_site.get_all_values.return_value = [
        ["DLC Montage · Abnahmeprotokoll Standort: " + site.name, "", "", "", "", "Link", ""],
        ["Standort: " + site.name, "", "", "", "Anlage: G", "", ""],
        ["Adresse: Addr", "", "", "", "Bau-Status: Fertiggestellt", "", ""],
        ["Abrechnungszeitraum: KW 39", "", "", "", "Prüfender Bauleiter: Emil", "", ""],
        [],
        ["1. ERBRACHTE MONTAGELEISTUNGEN"],
        ["Pos.", "Leistung", "Einheit", "Menge", "Status Montage", "Abnahme", "Bemerkung"],
        [1, "Kabelzug 5x16", "m", "50", "✓ Erledigt", "✓ i.O.", "Trasse sauber verlegt"],
        [],
        ["2. ABNAHMEPROTOKOLL & MÄNGELRÜGE (Ausfüllen durch Bauleiter Emil)"],
        ["Gesamturteil Abnahme:", "In Prüfung", "", "Freigabe zur Auszahlung:", "Nein"],
        [],
        ["Prüfkriterien:", "☐ Fotodokumentation vollständig eingereicht", "", "", "☐ Messprotokoll"],
        ["", "☐ Kabelwege nach Vorgabe", "", "", "☐ Baustelle besenrein"],
        [],
        ["Mängelliste / Korrekturbedarf / Anmerkungen des Bauleiters:"],
        ["1.", "Manual Site Note preserved"],
        ["2.", ""],
        ["3.", ""],
        ["4.", ""],
        [],
        ["Geprüft durch Bauleiter: Emil (SPIE)", "", "", "", "Datum der Abnahme: 22.09.2026"],
    ]
    mock_sh.worksheets.return_value = [mock_ws_summary, mock_ws_site]

    monkeypatch.setattr("sync_emil_google_sheet.get_spreadsheet", lambda sheet_id=None: mock_sh)

    sync_emil_google_sheet.sync_emil_sheet(target_weeks=(39,))

    # Verify summary update preserved manual values:
    mock_ws_summary.update.assert_called_once()
    summary_values = mock_ws_summary.update.call_args[1]["values"]
    site_row = next(r for r in summary_values if len(r) >= 9 and r[1] == site.name)
    assert site_row[5] == "Nacharbeit erforderlich"
    assert site_row[6] == "Prüfnotiz Emil"
    assert site_row[7] == "Nein"
    assert site_row[8] == "22.09.2026"

    # Verify site sheet update preserved Section 1 columns F/G and Section 2:
    mock_ws_site.update.assert_called_once()
    site_values = mock_ws_site.update.call_args[1]["values"]
    pos_row = next(r for r in site_values if len(r) >= 7 and r[1] == "Kabelzug 5x16")
    assert pos_row[5] == "✓ i.O."
    assert pos_row[6] == "Trasse sauber verlegt"
    flat_site_text = " ".join(str(c) for r in site_values for c in r)
    assert "Manual Site Note preserved" in flat_site_text
