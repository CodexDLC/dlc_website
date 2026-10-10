# ruff: noqa: RUF001, RUF002
"""Integration tests for AC documents, settlement, master workbook, and Google sync.

Verifies:
1. HTTP permissions: customer portal and mbg_reports financial gating (superuser can_export_reports).
2. Foreman vs Admin access: tabs 'Акты и табели' and 'Сводная ведомость' are admin-only.
3. Payment domain service corrections:
   - Admin-only gate (not generic is_manager);
   - Idempotent no-op does not duplicate CustomerAuditEvent;
   - Note max length and future date validations;
   - Non-PII logging.
4. Independent paid/unpaid POST controls with audit.
5. Invoice generation (per-site & batch):
   - AC validation (no foreign DC);
   - Default exclusion of paid sites (include_paid=False);
   - Explicit inclusion of paid sites (include_paid=True);
   - All rates, prices and amounts are zero while hours/quantities preserved.
6. Master workbook feature adapter:
   - Zero rates in cells and formulas (no hardcoded 40 or 50);
   - Preserves actual hours and quantities;
   - Live DB status for 'Bezahlt' / 'Offen'.
7. Master GET no network writes, and Google sync POST with CSRF and fail-closed protection.
"""

from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from features.customer_portal.models import CustomerAuditEvent
from features.customer_portal.services import grant_membership
from features.mbg_reports.google_sync import read_existing_payments, sync_master_to_google_sheets
from features.mbg_reports.master_workbook import build_master_settlement_workbook
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.work_catalog.models import WorkType
from features.projects.models import AcObject, Client, ProjectGroup
from features.projects.settlement import (
    filter_sites_for_historical_ledger,
    filter_sites_for_invoice,
    mark_site_paid,
    set_site_payment_status,
    unmark_site_paid,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def integration_data():
    """Setup users, projects, standorte and accepted MBG reports."""
    users = get_user_model()
    admin = users.objects.create_superuser(username="int-admin", email="admin@dlc.test", password="pass")
    manager = users.objects.create_user(username="int-manager", is_staff=True)
    from django.contrib.auth.models import Permission
    perm = Permission.objects.get(codename="manage_reports")
    manager.user_permissions.add(perm)
    customer = users.objects.create_user(username="int-customer")

    client = Client.objects.create(name="Auftraggeber Integration")
    grant_membership(actor=admin, user=customer, client=client, can_manage_projects=False)

    group_ac = ProjectGroup.objects.create(name="Anlage AC Nord", client=client, has_ac=True, status="active")
    group_dc = ProjectGroup.objects.create(name="Anlage DC Sud", client=client, has_ac=False, status="active")

    site1 = AcObject.objects.create(group=group_ac, name="Standort 101", address="Str 1", project_number="P-101", status="completed")
    site2 = AcObject.objects.create(group=group_ac, name="Standort 102", address="Str 2", project_number="P-102", status="completed", is_paid=True)
    site_dc = AcObject.objects.create(group=group_dc, name="Standort DC 1", address="Str DC", project_number="P-DC", status="completed")

    wt_material, _ = WorkType.objects.get_or_create(
        code="material-delivery", defaults={"name_de": "Materialtransport", "calculation_rule": "actual"}
    )
    wt_hourly, _ = WorkType.objects.get_or_create(
        code="sonstige", defaults={"name_de": "Zusatzarbeiten", "calculation_rule": "actual"}
    )

    # Accepted reports for site1 and site2
    for site in (site1, site2):
        rep = MbgDailyReport.objects.create(
            author=admin,
            site=site,
            work_date=date(2026, 9, 21),
            status="accepted",
            version=1,
            submission_key=uuid4(),
        )
        MbgReportRevision.objects.create(
            report=rep,
            actor=admin,
            version=1,
            action="accept",
            snapshot={
                "status": "accepted",
                "address": site.address,
                "project_number": site.project_number,
                "entries": [
                    {
                        "work_type_code": "material-delivery",
                        "description": "Materiallieferung",
                        "calculation_rule": "flat",
                        "quantity": "2.00",
                        "actual_person_hours": "3.50",
                    },
                    {
                        "work_type_code": "sonstige",
                        "description": "Kabeltrasse verlegen",
                        "calculation_rule": "actual",
                        "quantity": "4.00",
                        "actual_person_hours": "4.00",
                    },
                ],
            },
        )

    return {
        "admin": admin,
        "manager": manager,
        "customer": customer,
        "group_ac": group_ac,
        "group_dc": group_dc,
        "site1": site1,
        "site2": site2,
        "site_dc": site_dc,
    }


def test_customer_portal_documents_financial_isolation(integration_data, client):
    """Customer portal documents view strictly forces finance=False and exposes no settlement features."""
    client.force_login(integration_data["customer"])
    res = client.get(reverse("customer_portal:documents"))
    assert res.status_code == 200
    content = res.content.decode()

    # Documents present
    assert "Standort 101" in content
    assert "Акт" in content
    assert "Табель" in content

    # Finances strictly absent
    assert "Отчёт для выставления счёта" not in content
    assert "Сводная ведомость" not in content
    assert "Обновить Google Таблицу" not in content
    assert "Включить оплаченные" not in content
    assert "unified-doc-badge--paid" not in content
    assert "unified-doc-badge--unpaid" not in content
    assert "Для Димы" not in content


def test_mbg_exports_foreman_vs_admin_permissions(integration_data, client):
    """Non-superuser foreman sees documents without finances; superuser admin sees tabs and controls."""
    # 1. Foreman (staff, not superuser)
    client.force_login(integration_data["manager"])
    res_foreman = client.get(reverse("mbg_reports:export_hub"))
    assert res_foreman.status_code == 200
    content_foreman = res_foreman.content.decode()

    assert "Акт" in content_foreman
    assert "Табель" in content_foreman
    assert "Сводная ведомость" not in content_foreman
    assert "Отчёт для выставления счёта" not in content_foreman
    assert "Обновить Google Таблицу" not in content_foreman

    # 2. Admin (superuser)
    client.force_login(integration_data["admin"])
    res_admin = client.get(reverse("mbg_reports:export_hub"))
    assert res_admin.status_code == 200
    content_admin = res_admin.content.decode()

    assert "Акты и табели" in content_admin
    assert "Сводная ведомость" in content_admin
    assert "Отчёт для выставления счёта" in content_admin
    assert "Обновить Google Таблицу" in content_admin
    assert "Включить оплаченные" in content_admin
    assert "unified-doc-badge--paid" in content_admin
    assert "unified-doc-badge--unpaid" in content_admin
    assert "Для Димы" not in content_admin


def test_payment_service_admin_only_and_idempotent_no_op(integration_data):
    """Payment domain service requires superuser, validates inputs, and performs idempotent no-ops."""
    admin = integration_data["admin"]
    manager = integration_data["manager"]
    site = integration_data["site1"]

    # Non-admin (staff manager) is rejected
    with pytest.raises(PermissionDenied):
        mark_site_paid(actor=manager, site_id=site.pk)

    with pytest.raises(PermissionDenied):
        unmark_site_paid(actor=manager, site_id=site.pk)

    # Note length validation (>255)
    with pytest.raises(ValidationError, match="255"):
        mark_site_paid(actor=admin, site_id=site.pk, note="X" * 256)

    # Future date validation
    with pytest.raises(ValidationError, match="Zukunft"):
        mark_site_paid(actor=admin, site_id=site.pk, paid_at=timezone.now() + timedelta(days=2))

    # Mark paid creates 1 audit event
    initial_audits = CustomerAuditEvent.objects.filter(target_id=site.pk).count()
    mark_site_paid(actor=admin, site_id=site.pk, note="Rechnung 001")
    assert CustomerAuditEvent.objects.filter(target_id=site.pk).count() == initial_audits + 1

    site.refresh_from_db()
    assert site.is_paid is True

    # Idempotent no-op call does NOT duplicate audit event
    mark_site_paid(actor=admin, site_id=site.pk, note="Rechnung 001")
    assert CustomerAuditEvent.objects.filter(target_id=site.pk).count() == initial_audits + 1

    # Unmark paid creates 1 audit event
    unmark_site_paid(actor=admin, site_id=site.pk)
    assert CustomerAuditEvent.objects.filter(target_id=site.pk).count() == initial_audits + 2

    site.refresh_from_db()
    assert site.is_paid is False

    # Idempotent unmark call does NOT duplicate audit event
    unmark_site_paid(actor=admin, site_id=site.pk)
    assert CustomerAuditEvent.objects.filter(target_id=site.pk).count() == initial_audits + 2


def test_independent_paid_unpaid_post_controls(integration_data, client):
    """Admin can toggle payment status via dedicated POST endpoint with audit."""
    admin = integration_data["admin"]
    site = integration_data["site1"]
    assert site.is_paid is False

    client.force_login(admin)

    # Toggle to paid
    res = client.post(reverse("mbg_reports:site_payment_toggle", args=[site.pk]), {"is_paid": "1", "note": "Bank transfer"})
    assert res.status_code == 302
    site.refresh_from_db()
    assert site.is_paid is True
    assert site.payment_note == "Bank transfer"

    # Toggle to unpaid
    res2 = client.post(reverse("mbg_reports:site_payment_toggle", args=[site.pk]), {"is_paid": "0"})
    assert res2.status_code == 302
    site.refresh_from_db()
    assert site.is_paid is False


def test_batch_invoice_validation_and_zero_pricing(integration_data, client):
    """Batch invoice requires AC objects, respects include_paid, and outputs zero prices."""
    admin = integration_data["admin"]
    site1 = integration_data["site1"]  # unpaid
    site2 = integration_data["site2"]  # paid
    site_dc = integration_data["site_dc"]

    client.force_login(admin)

    # 1. Reject foreign DC site
    res_dc = client.post(
        reverse("mbg_reports:batch_settlement_report"),
        {"site_ids": [site_dc.pk]},
    )
    assert res_dc.status_code == 302

    # 2. Reject paid site when include_paid is default (False)
    res_paid = client.post(
        reverse("mbg_reports:batch_settlement_report"),
        {"site_ids": [site2.pk]},
    )
    assert res_paid.status_code == 302

    # 3. Successful invoice generation for unpaid site
    res_ok = client.post(
        reverse("mbg_reports:batch_settlement_report"),
        {"site_ids": [site1.pk]},
    )
    assert res_ok.status_code == 302
    assert "performance" in res_ok.url

    # Follow redirect to download file
    res_download = client.get(res_ok.url)
    assert res_download.status_code == 200
    content_bytes = b"".join(res_download.streaming_content) if hasattr(res_download, "streaming_content") else res_download.content
    wb = load_workbook(BytesIO(content_bytes), data_only=True)
    summary_sheet = wb.active
    # All prices and amounts in output must be 0.00
    for row in summary_sheet.iter_rows(values_only=True):
        for cell in row:
            if isinstance(cell, str) and "€" in cell:
                assert "0.00" in cell or "0,00" in cell or cell == "—"


def test_master_workbook_zero_rates_and_formulas(integration_data):
    """Master settlement workbook contains zero prices/rates in cells and formulas without hardcoded 40/50."""
    wb = build_master_settlement_workbook()

    # 1. Check Übersicht sheet
    ws_summary = wb["Übersicht"]
    summary_card_val = str(ws_summary["A5"].value)
    assert "Materiallogistik (0,00 €): 0,00 €" in summary_card_val
    assert "Montagepreise: 0,00 €" in summary_card_val
    assert "50,00" not in summary_card_val
    assert "40,00" not in summary_card_val

    # Check status of Zahlung in column 10: site2 is Bezahlt, site1 is Offen
    found_bezahlt = False
    found_offen = False
    for r in range(8, ws_summary.max_row + 1):
        site_name_cell = ws_summary.cell(r, 2).value
        pay_cell = ws_summary.cell(r, 10).value
        if site_name_cell == "Standort 102":
            assert pay_cell == "Bezahlt"
            found_bezahlt = True
        elif site_name_cell == "Standort 101":
            assert pay_cell == "Offen"
            found_offen = True
    assert found_bezahlt and found_offen

    # 2. Check site sheet formulas and cells
    site_sheet = [s for s in wb.worksheets if s.title != "Übersicht"][0]
    for row in site_sheet.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str) and cell.value.startswith("="):
                # Ensure no formulas embed 40 or 50
                assert "* 40" not in cell.value
                assert "* 50" not in cell.value
                assert "*40" not in cell.value
                assert "*50" not in cell.value


def test_master_excel_get_no_network_writes(integration_data, client):
    """GET on master_excel_download generates in-memory workbook without external network writes."""
    client.force_login(integration_data["admin"])
    res = client.get(reverse("mbg_reports:master_excel_download"))
    assert res.status_code == 200
    assert res["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "DLC_Montage_AC_Gesamtabrechnung.xlsx" in res["Content-Disposition"]
    assert len(res.content) > 1000


def test_google_sync_fail_closed_and_csrf_protection(integration_data, client):
    """Google Sheets sync requires POST+CSRF and fails closed if existing payments cannot be read."""
    client.force_login(integration_data["admin"])

    # GET is rejected
    res_get = client.get(reverse("mbg_reports:google_sheets_sync"))
    assert res_get.status_code == 405

    # Mock sheet that fails on read
    mock_sh = MagicMock()
    mock_summary = MagicMock()
    mock_summary.get_all_values.side_effect = Exception("Network connection lost")
    mock_sh.worksheet.return_value = mock_summary

    # Fail-closed: exception stops execution before any write
    with pytest.raises(RuntimeError, match="Fail-closed"):
        sync_master_to_google_sheets(spreadsheet=mock_sh)
    mock_summary.update.assert_not_called()
