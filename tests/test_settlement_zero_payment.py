# ruff: noqa: RUF003
"""Тесты доменной логики оплат Standort, нулевых финансовых расценок и контрактов выборки."""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from features.customer_portal.models import CustomerAuditEvent
from features.mbg_reports.completion_projection import CompletionRow
from features.mbg_reports.export_services import (
    generate_performance_report,
    generate_site_performance_report,
)
from features.mbg_reports.models import MbgDailyReport, PerformanceExport
from features.mbg_reports.pricing_projection import price_completion_row
from features.mbg_reports.reporting_facts import calc_entry_amount
from features.mbg_reports.reporting_selectors import (
    compute_site_snapshot_digest,
    load_accepted_reports_dataset,
)
from features.mbg_reports.services import review_report, save_report
from features.projects.models import AcObject, Client, ProjectGroup
from features.projects.settlement import (
    filter_sites_for_historical_ledger,
    filter_sites_for_invoice,
    get_site_payment_status,
    mark_site_paid,
    set_site_payment_status,
    unmark_site_paid,
)
from features.staff.models import Employee
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def settlement_setup():
    User = get_user_model()
    admin = User.objects.create_user(username="admin_settler", is_superuser=True)
    regular_user = User.objects.create_user(username="regular_worker", is_superuser=False)
    client = Client.objects.create(name="Stadtwerke Energie")
    group = ProjectGroup.objects.create(name="Anlage Solarpark A", client=client, has_ac=True, status="active")
    site_a = AcObject.objects.create(
        group=group,
        name="Haus 10A",
        address="Sonnenallee 10A",
        project_number="P-10A",
        status="started",
    )
    site_b = AcObject.objects.create(
        group=group,
        name="Haus 10B",
        address="Sonnenallee 10B",
        project_number="P-10B",
        status="started",
    )
    worker = Employee.objects.create(first_name="Hans", last_name="Bauer", has_ac_access=True)
    return {
        "admin": admin,
        "regular_user": regular_user,
        "client": client,
        "group": group,
        "site_a": site_a,
        "site_b": site_b,
        "worker": worker,
    }


def _create_accepted_report(actor, worker, site, work_date, entries):
    report = save_report(
        actor=actor,
        site=site,
        work_date=work_date,
        workforce=[worker],
        entries=entries,
        submit=True,
    )
    return review_report(actor=actor, report_id=report.pk, version=report.version, decision="accept")


def test_independent_payment_per_standort(settlement_setup):
    """Оплата устанавливается строго на уровне Standort (AcObject), никогда не на уровне ProjectGroup."""
    admin = settlement_setup["admin"]
    site_a = settlement_setup["site_a"]
    site_b = settlement_setup["site_b"]
    group = settlement_setup["group"]

    assert site_a.is_paid is False
    assert site_b.is_paid is False
    assert not hasattr(group, "is_paid")

    mark_site_paid(actor=admin, site_id=site_a.pk, note="Rechnung R-2026-01 bezahlt")

    site_a.refresh_from_db()
    site_b.refresh_from_db()

    assert site_a.is_paid is True
    assert site_a.paid_at is not None
    assert site_a.paid_by == admin
    assert site_a.payment_note == "Rechnung R-2026-01 bezahlt"

    # Второй Standort той же группы остаётся неоплаченным
    assert site_b.is_paid is False
    assert site_b.paid_at is None
    assert site_b.paid_by is None


def test_payment_authorization_and_audit(settlement_setup):
    """Только авторизованный менеджер может менять оплату, каждое изменение логируется в CustomerAuditEvent."""
    admin = settlement_setup["admin"]
    regular = settlement_setup["regular_user"]
    site_a = settlement_setup["site_a"]

    # Неавторизованный пользователь получает PermissionDenied
    with pytest.raises(PermissionDenied):
        mark_site_paid(actor=regular, site_id=site_a.pk)

    with pytest.raises(PermissionDenied):
        unmark_site_paid(actor=regular, site_id=site_a.pk)

    with pytest.raises(PermissionDenied):
        set_site_payment_status(actor=regular, site_id=site_a.pk, is_paid=True)

    # Авторизованный менеджер отмечает оплату
    fixed_time = timezone.now() - timedelta(days=1)
    mark_site_paid(
        actor=admin,
        site_id=site_a.pk,
        paid_at=fixed_time,
        note="Überweisung erhalten",
        reason="Zahlungseingang",
    )

    site_a.refresh_from_db()
    assert site_a.is_paid is True
    assert site_a.paid_at == fixed_time
    assert site_a.payment_note == "Überweisung erhalten"

    audit_marked = CustomerAuditEvent.objects.filter(
        target_type="AcObject",
        target_id=site_a.pk,
        action="site_payment_marked",
    ).first()
    assert audit_marked is not None
    assert audit_marked.actor == admin
    assert audit_marked.client == settlement_setup["client"]
    assert audit_marked.before.get("is_paid") is False
    assert audit_marked.after.get("is_paid") is True
    assert audit_marked.reason == "Zahlungseingang"

    # Менеджер снимает отметку об оплате
    unmark_site_paid(actor=admin, site_id=site_a.pk, reason="Rücklastschrift")
    site_a.refresh_from_db()
    assert site_a.is_paid is False
    assert site_a.paid_at is None
    assert site_a.paid_by is None
    assert site_a.payment_note == ""

    audit_unmarked = CustomerAuditEvent.objects.filter(
        target_type="AcObject",
        target_id=site_a.pk,
        action="site_payment_unmarked",
    ).first()
    assert audit_unmarked is not None
    assert audit_unmarked.before.get("is_paid") is True
    assert audit_unmarked.after.get("is_paid") is False
    assert audit_unmarked.reason == "Rücklastschrift"


def test_payment_does_not_alter_site_completion_or_accepted_snapshots(settlement_setup):
    """Отметка оплаты не меняет статус готовности (completed) и не инвалидирует снимок/хеш принятых отчётов."""
    admin = settlement_setup["admin"]
    worker = settlement_setup["worker"]
    site_a = settlement_setup["site_a"]

    work = WorkType.objects.get(code="photo-documentation")
    entries = [{
        "participants": [worker],
        "starts_at": time(9, 0),
        "ends_at": time(10, 0),
        "work_type": work,
        "description": "Fotodokumentation Fertigstellung",
        "quantity": Decimal("1"),
    }]
    _create_accepted_report(admin, worker, site_a, date(2026, 9, 21), entries)

    site_a.status = "completed"
    site_a.save(update_fields=["status"])

    site_a.refresh_from_db()
    assert site_a.status == "completed"

    digest_before = compute_site_snapshot_digest(site_a)
    assert digest_before != ""

    report = MbgDailyReport.objects.get(site=site_a)
    report_version_before = report.version
    snapshot_before = report.revisions.get(version=report.version).snapshot

    # Отмечаем оплату
    mark_site_paid(actor=admin, site_id=site_a.pk)

    site_a.refresh_from_db()
    report.refresh_from_db()
    snapshot_after = report.revisions.get(version=report.version).snapshot

    # Completed Standort paid stays completed and viewable
    assert site_a.status == "completed"
    assert report.version == report_version_before
    assert snapshot_after == snapshot_before
    assert compute_site_snapshot_digest(site_a) == digest_before

    # Снимаем оплату
    unmark_site_paid(actor=admin, site_id=site_a.pk)

    site_a.refresh_from_db()
    assert site_a.status == "completed"
    assert compute_site_snapshot_digest(site_a) == digest_before


def test_domain_selection_contract_excludes_paid_by_default(settlement_setup, monkeypatch, tmp_path):
    """Селектор для новых счетов (Invoices / Leistungsnachweis) по умолчанию исключает оплаченные Standorte."""
    monkeypatch.setattr(PerformanceExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin = settlement_setup["admin"]
    worker = settlement_setup["worker"]
    group = settlement_setup["group"]
    site_a = settlement_setup["site_a"]
    site_b = settlement_setup["site_b"]

    work = WorkType.objects.get(code="photo-documentation")
    _create_accepted_report(admin, worker, site_a, date(2026, 9, 21), [{
        "participants": [worker], "starts_at": time(8), "ends_at": time(9),
        "work_type": work, "description": "Doku A", "quantity": Decimal("1"),
    }])
    _create_accepted_report(admin, worker, site_b, date(2026, 9, 22), [{
        "participants": [worker], "starts_at": time(9), "ends_at": time(10),
        "work_type": work, "description": "Doku B", "quantity": Decimal("1"),
    }])

    site_a.status = "completed"
    site_a.save(update_fields=["status"])
    site_b.status = "completed"
    site_b.save(update_fields=["status"])

    # site_a оплачен, site_b не оплачен
    mark_site_paid(actor=admin, site_id=site_a.pk)

    # 1. Селектор filter_sites_for_invoice по умолчанию возвращает только site_b
    invoice_sites_default = list(filter_sites_for_invoice(group_id=group.pk))
    assert invoice_sites_default == [site_b]

    # С явным include_paid=True возвращаются оба
    invoice_sites_all = list(filter_sites_for_invoice(group_id=group.pk, include_paid=True))
    assert set(invoice_sites_all) == {site_a, site_b}

    # 2. Экспорт generate_performance_report: по умолчанию исключает оплаченный site_a
    report_default = generate_performance_report(actor=admin, group_id=group.pk, include_paid=False)
    assert len(report_default.snapshot["sites"]) == 1
    assert report_default.snapshot["sites"][0]["site_id"] == site_b.pk

    # С include_paid=True включает оба
    report_with_paid = generate_performance_report(actor=admin, group_id=group.pk, include_paid=True)
    assert len(report_with_paid.snapshot["sites"]) == 2
    site_ids_in_export = {s["site_id"] for s in report_with_paid.snapshot["sites"]}
    assert site_ids_in_export == {site_a.pk, site_b.pk}

    # 3. Экспорт для одного объекта generate_site_performance_report
    # Оплаченный site_a при include_paid=False вызывает ошибку
    with pytest.raises(ValidationError):
        generate_site_performance_report(actor=admin, site_id=site_a.pk, include_paid=False)

    single_with_paid = generate_site_performance_report(actor=admin, site_id=site_a.pk, include_paid=True)
    assert single_with_paid.snapshot["sites"][0]["site_id"] == site_a.pk


def test_master_historical_ledger_retains_paid_with_flag(settlement_setup):
    """Исторический сводный регистр (Gesamtabrechnung) сохраняет все Standorte с явным флагом оплаты."""
    admin = settlement_setup["admin"]
    worker = settlement_setup["worker"]
    group = settlement_setup["group"]
    site_a = settlement_setup["site_a"]
    site_b = settlement_setup["site_b"]

    work = WorkType.objects.get(code="photo-documentation")
    _create_accepted_report(admin, worker, site_a, date(2026, 9, 21), [{
        "participants": [worker], "starts_at": time(8), "ends_at": time(9),
        "work_type": work, "description": "Doku A", "quantity": Decimal("1"),
    }])
    _create_accepted_report(admin, worker, site_b, date(2026, 9, 22), [{
        "participants": [worker], "starts_at": time(9), "ends_at": time(10),
        "work_type": work, "description": "Doku B", "quantity": Decimal("1"),
    }])

    site_a.status = "completed"
    site_a.save(update_fields=["status"])
    site_b.status = "completed"
    site_b.save(update_fields=["status"])

    mark_site_paid(actor=admin, site_id=site_a.pk)

    # filter_sites_for_historical_ledger возвращает оба объекта
    ledger_sites = list(filter_sites_for_historical_ledger(group_id=group.pk))
    assert set(ledger_sites) == {site_a, site_b}

    # load_accepted_reports_dataset сохраняет оба объекта
    dataset = load_accepted_reports_dataset(site_ids=[site_a.pk, site_b.pk])
    assert set(dataset.all_sites.keys()) == {site_a.pk, site_b.pk}

    sum_a = dataset.all_sites[site_a.pk]
    sum_b = dataset.all_sites[site_b.pk]
    assert sum_a.is_paid is True
    assert sum_b.is_paid is False

    # get_site_payment_status возвращает структурированный статус
    status_a = get_site_payment_status(site_a.pk)
    status_b = get_site_payment_status(site_b.pk)
    assert status_a["is_paid"] is True
    assert status_a["paid_by_id"] == admin.pk
    assert status_b["is_paid"] is False


def test_all_new_financial_mbg_rates_and_amounts_are_zero():
    """Все новые финансовые цены/ставки/суммы MBG равны 0.00 €, включая транспорт (бывшие 50 €) и почасовые."""
    # 1. Доставка материалов (transport formerly 50.00 €)
    delivery_row = CompletionRow(
        kind="flat",
        work_item_id=None,
        name="Materiallieferung",
        unit="psch.",
        quantity=Decimal("3"),
        actual_person_hours=Decimal("4.5"),
        route="",
        cable_type="",
        sources=({"work_type_code": "material-delivery", "calculation_rule": "flat"},),
    )
    res_deliv = price_completion_row(delivery_row)
    assert res_deliv.unit_price == Decimal("0.00")
    assert res_deliv.amount == Decimal("0.00")

    entry_data_deliv = {"work_type_code": "material-delivery", "quantity": Decimal("2")}
    assert calc_entry_amount(entry_data_deliv) == Decimal("0.00")

    # 2. Почасовые работы (hourly rates formerly 40.00 €)
    hourly_row = CompletionRow(
        kind="hourly",
        work_item_id=None,
        name="Sonstige Stunden",
        unit="Std.",
        quantity=Decimal("5"),
        actual_person_hours=Decimal("5"),
        route="",
        cable_type="",
        sources=({"work_type_code": "sonstige", "calculation_rule": "actual"},),
    )
    res_hourly = price_completion_row(hourly_row)
    assert res_hourly.unit_price == Decimal("0.00")
    assert res_hourly.amount == Decimal("0.00")

    # 3. Сдельные каталожные работы
    piece_row = CompletionRow(
        kind="piecework",
        work_item_id=None,
        name="Kabelverlegung",
        unit="m",
        quantity=Decimal("120"),
        actual_person_hours=Decimal("8"),
        route="",
        cable_type="",
        sources=({"work_type_code": "cable-laying", "calculation_rule": "cable"},),
    )
    res_piece = price_completion_row(piece_row)
    assert res_piece.unit_price == Decimal("0.00")
    assert res_piece.amount == Decimal("0.00")

    # Фактические часы и объёмы не искажаются
    assert delivery_row.actual_person_hours == Decimal("4.5")
    assert delivery_row.quantity == Decimal("3")
    assert hourly_row.actual_person_hours == Decimal("5")
    assert piece_row.quantity == Decimal("120")


def test_unknown_quantity_stays_unknown_not_zero_or_one():
    """Неизвестный объём (None) остаётся None; не подменяется на 0 или 1."""
    unknown_row = CompletionRow(
        kind="piecework",
        work_item_id=None,
        name="Ungeklärte Trasse",
        unit="m",
        quantity=None,  # Unknown quantity
        actual_person_hours=Decimal("2"),
        route="",
        cable_type="",
        sources=({"work_type_code": "cable-tray", "calculation_rule": "tray"},),
    )
    assert unknown_row.quantity is None

    res = price_completion_row(unknown_row)
    assert res.unit_price == Decimal("0.00")
    assert res.amount is None
    assert unknown_row.quantity is None


@pytest.mark.parametrize("language", ["ru", "de"])
def test_suppress_historical_embedded_prices_in_new_artifacts(settlement_setup, monkeypatch, tmp_path, language):
    """При создании новых артефактов исторические зашитые цены (50 € / 40 €) подавляются в 0.00 €."""
    from django.utils.translation import activate

    activate(language)
    monkeypatch.setattr(PerformanceExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin = settlement_setup["admin"]
    worker = settlement_setup["worker"]
    group = settlement_setup["group"]
    site = settlement_setup["site_a"]

    # Создаём принятый отчёт, в котором исторический снимок мог содержать старые цены
    material_work = WorkType.objects.get(code="material-delivery")
    report = save_report(
        actor=admin,
        site=site,
        work_date=date(2026, 9, 21),
        workforce=[worker],
        entries=[{
            "participants": [worker],
            "starts_at": time(8),
            "ends_at": time(9),
            "work_type": material_work,
            "description": "Materiallieferung",
            "quantity": Decimal("2"),
            "unit_price": Decimal("50.00"),
            "amount": Decimal("100.00"),
        }],
        submit=True,
    )
    review_report(actor=admin, report_id=report.pk, version=report.version, decision="accept")

    site.status = "completed"
    site.save(update_fields=["status"])

    # Генерируем новый артефакт
    artifact = generate_performance_report(actor=admin, group_id=group.pk, include_paid=True)

    site_data = artifact.snapshot["sites"][0]
    assert site_data["known_subtotal"] == "0.00"
    assert site_data["amount"] == "0.00"

    row_data = site_data["rows"][0]
    # Зашитая историческая цена 50.00 подавлена в 0.00
    assert row_data["unit_price"] == "0.00"
    assert row_data["amount"] == "0.00"


def test_fingerprint_distinguishes_zero_version_and_include_paid(settlement_setup, monkeypatch, tmp_path):
    """Отпечатки (fingerprints) различают нулевую версию ценообразования и опцию include_paid."""
    monkeypatch.setattr(PerformanceExport._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin = settlement_setup["admin"]
    worker = settlement_setup["worker"]
    group = settlement_setup["group"]
    site_a = settlement_setup["site_a"]
    site_b = settlement_setup["site_b"]

    work = WorkType.objects.get(code="photo-documentation")
    _create_accepted_report(admin, worker, site_a, date(2026, 9, 21), [{
        "participants": [worker], "starts_at": time(8), "ends_at": time(9),
        "work_type": work, "description": "Doku A", "quantity": Decimal("1"),
    }])
    _create_accepted_report(admin, worker, site_b, date(2026, 9, 22), [{
        "participants": [worker], "starts_at": time(9), "ends_at": time(10),
        "work_type": work, "description": "Doku B", "quantity": Decimal("1"),
    }])

    site_a.status = "completed"
    site_a.save(update_fields=["status"])
    site_b.status = "completed"
    site_b.save(update_fields=["status"])

    mark_site_paid(actor=admin, site_id=site_a.pk)

    # Экспорт с include_paid=False и include_paid=True должны иметь РАЗНЫЕ fingerprints
    art_unpaid = generate_performance_report(actor=admin, group_id=group.pk, include_paid=False)
    art_all = generate_performance_report(actor=admin, group_id=group.pk, include_paid=True)

    assert art_unpaid.fingerprint != art_all.fingerprint
    assert art_unpaid.template_version == "ac-perf-zero-1"
    assert art_all.template_version == "ac-perf-zero-1"
