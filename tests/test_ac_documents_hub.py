"""Тесты интеграции раздела «Документы» AC: левое меню, отсутствие переключателя в журнале,
компактный экран в стиле customer_portal/documents, поиск, пагинация, права и сохранение экспортов.
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from features.customer_portal.services import grant_membership
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision, PerformanceExport, WeeklyExport
from features.projects.models import AcObject, Client, ProjectGroup, SiteWorkItem
from features.staff.models import Employee
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


@pytest.fixture
def documents_hub_setup():
    users = get_user_model()
    admin = users.objects.create_superuser(username="ac-admin", email="admin@dlc.test", password=None)

    # Клиент заказчика
    client_org = Client.objects.create(name="Auftraggeber Sol")
    customer_user = users.objects.create_user(username="sol-customer")
    grant_membership(actor=admin, user=customer_user, client=client_org, can_manage_projects=True)

    # Бригадир (Vorarbeiter) с доступом к AC, но не superuser
    foreman_user = users.objects.create_user(username="ac-foreman")
    Employee.objects.create(
        user=foreman_user,
        first_name="Hans",
        last_name="Foreman",
        employment_status="active",
        is_foreman=True,
        has_ac_access=True,
    )

    # Проект и объекты AC
    group_alpha = ProjectGroup.objects.create(
        name="Anlage Alpha AC",
        client=client_org,
        address="Sonnenweg 1, Berlin",
        status="active",
        has_ac=True,
    )
    group_beta = ProjectGroup.objects.create(
        name="Anlage Beta AC",
        client=client_org,
        address="Sternstraße 5, Berlin",
        status="active",
        has_ac=True,
    )

    site_a1 = AcObject.objects.create(
        group=group_alpha,
        name="Standort A1",
        address="Sonnenweg 1A",
        project_number="P-A1",
        status="started",
    )
    site_b1 = AcObject.objects.create(
        group=group_beta,
        name="Standort B1",
        address="Sternstraße 5A",
        project_number="P-B1",
        status="completed",
    )

    work_type = WorkType.objects.create(
        code="ac_inverter",
        name_ru="Монтаж инвертора",
        name_de="Wechselrichter Montage",
        unit="Stk",
    )
    SiteWorkItem.objects.create(
        site=site_a1,
        work_type=work_type,
        planned_quantity=1,
        unit_snapshot="Stk",
        is_required=True,
    )

    # Принятый отчёт для site_a1
    report = MbgDailyReport.objects.create(
        author=admin,
        site=site_a1,
        work_date=date(2026, 9, 21),
        status="accepted",
        version=1,
        submission_key=uuid4(),
    )
    MbgReportRevision.objects.create(
        report=report,
        version=1,
        actor=admin,
        snapshot={
            "status": "accepted",
            "site_name": site_a1.name,
            "group_name": group_alpha.name,
            "address": site_a1.address,
            "project_number": site_a1.project_number,
            "entries": [
                {
                    "work_type_code": "ac_inverter",
                    "description": "Wechselrichter Montage",
                    "completed_quantity": "1",
                    "unit": "Stk",
                    "actual_person_hours": "2.0",
                    "calculation_rule": "piecework",
                }
            ],
        },
    )

    from features.mbg_reports.models import CURRENT_WEEKLY_EXPORT_TEMPLATE

    # Недельный экспорт для проверки ссылки скачивания
    weekly_exp = WeeklyExport.objects.create(
        year=2026,
        week=39,
        fingerprint=uuid4().hex,
        template_version=CURRENT_WEEKLY_EXPORT_TEMPLATE,
        snapshot={},
        author=admin,
        filename="mbg-week-2026-39.xlsx",
    )

    # Артефакт Leistungsnachweis для истории
    perf_art = PerformanceExport.objects.create(
        author=admin,
        group=group_alpha,
        filename="work-completion-alpha.xlsx",
        fingerprint=uuid4().hex,
        document_type="work_completion",
        snapshot={
            "scope": "group",
            "group_name": group_alpha.name,
        },
    )

    return {
        "admin": admin,
        "customer": customer_user,
        "foreman": foreman_user,
        "group_alpha": group_alpha,
        "group_beta": group_beta,
        "site_a1": site_a1,
        "site_b1": site_b1,
        "report": report,
        "weekly_export": weekly_exp,
        "perf_artifact": perf_art,
    }


def test_ac_left_sidebar_has_documents_entry(documents_hub_setup, client):
    """В левом меню пространства AC есть пункт 'Документы', ведущий на exports URL."""
    client.force_login(documents_hub_setup["admin"])
    response = client.get("/ru/cabinet/ac/dashboard/")
    assert response.status_code == 200
    content = response.content.decode()

    exports_url = reverse("mbg_reports:export_hub")
    reports_url = reverse("mbg_reports:list")

    # Проверяем именно блок левого меню nav
    assert '<nav class="cab-sidebar__nav"' in content
    sidebar_part = content[content.index('<nav class="cab-sidebar__nav"'):content.index('</nav>')]

    # В боковой панели присутствуют и 'Отчёты MBG', и 'Документы'
    assert reports_url in sidebar_part
    assert exports_url in sidebar_part
    assert "Документы" in sidebar_part


def test_mbg_reports_journal_has_no_export_excel_switcher(documents_hub_setup, client):
    """В журнале MBG отсутствует переключатель 'Экспорт Excel' (mbg-section-nav)."""
    client.force_login(documents_hub_setup["admin"])
    response = client.get(reverse("mbg_reports:list"))
    assert response.status_code == 200
    content = response.content.decode()

    # Переключатель вкладок 'Экспорт Excel' удален из журнала
    assert "Экспорт Excel" not in content
    assert "mbg-section-nav" not in content


def test_ac_documents_hub_permissions_customer_foreman_admin(documents_hub_setup, client):
    """Права доступа: Заказчик -> 403/Redirect, Бригадир -> 403, Администратор -> 200."""
    exports_url = reverse("mbg_reports:export_hub")

    # 1. Заказчик не имеет доступа во внутренний экспорт AC
    client.force_login(documents_hub_setup["customer"])
    resp_cust = client.get(exports_url)
    assert resp_cust.status_code in (403, 302)

    # 2. Бригадир (не superuser) получает 403 Forbidden
    client.force_login(documents_hub_setup["foreman"])
    resp_foreman = client.get(exports_url)
    assert resp_foreman.status_code == 403

    # 3. Администратор (superuser) имеет доступ
    client.force_login(documents_hub_setup["admin"])
    resp_admin = client.get(exports_url)
    assert resp_admin.status_code == 200


def test_ac_documents_hub_compact_left_aligned_layout(documents_hub_setup, client):
    """Экран экспортов оформлен в стиле customer_portal/documents: компактный левый контейнер и заголовок Документы."""
    client.force_login(documents_hub_setup["admin"])
    response = client.get(reverse("mbg_reports:export_hub"))
    assert response.status_code == 200
    content = response.content.decode()

    # Компактный контейнер и стили портала
    assert "customer-documents-content" in content
    assert "customer-portal-shell" in content
    assert "customer-header" in content

    # Заголовок страницы 'Документы' (вместо прежнего 'Экспорт Excel')
    assert "<h1>Документы</h1>" in content or "Документы" in content

    # Сохранены все 4 секции
    assert "Недельный табель часов" in content
    assert "Отчёт о выполненных работах" in content
    assert "Промежуточный акт" in content
    assert "Итоговый Leistungsnachweis" in content or "Итоговый почасовой отчёт" in content


def test_ac_documents_hub_search_and_pagination(documents_hub_setup, client):
    """Поиск и серверная пагинация фильтруют списки и сохраняют параметры запроса."""
    admin = documents_hub_setup["admin"]

    # Создаем дополнительные недели для проверки пагинации
    for w in range(1, 15):
        d = date(2026, 1, 5) + timedelta(weeks=w)
        rep = MbgDailyReport.objects.create(
            author=admin,
            site=documents_hub_setup["site_a1"],
            work_date=d,
            status="accepted",
            version=1,
            submission_key=uuid4(),
        )
        MbgReportRevision.objects.create(
            report=rep,
            version=1,
            actor=admin,
            snapshot={"status": "accepted", "entries": []},
        )

    client.force_login(admin)

    # 1. Поиск по проекту 'Alpha'
    resp_search = client.get(reverse("mbg_reports:export_hub") + "?q=Alpha")
    assert resp_search.status_code == 200
    content_search = resp_search.content.decode()
    assert "Anlage Alpha AC" in content_search

    # 2. Пагинация недель (страница 2)
    resp_page2 = client.get(reverse("mbg_reports:export_hub") + "?page_weeks=2&q=Alpha")
    assert resp_page2.status_code == 200
    content_page2 = resp_page2.content.decode()
    # Элементы пагинации присутствуют и содержат параметр q=Alpha
    assert "customer-pagination" in content_page2 or "page_weeks=" in content_page2
    assert "q=Alpha" in content_page2


def test_ac_documents_hub_preserves_all_export_links_and_js(documents_hub_setup, client):
    """Все существующие ссылки выгрузок, действия и JS сохранены без изменений."""
    client.force_login(documents_hub_setup["admin"])
    response = client.get(reverse("mbg_reports:export_hub"))
    assert response.status_code == 200
    content = response.content.decode()

    # 1. Ссылка на скачивание недели
    assert reverse("mbg_reports:download", args=[documents_hub_setup["weekly_export"].pk]) in content

    # 2. Ссылка генерации недели
    assert reverse("mbg_reports:exports") in content

    # 3. Действия Leistungsnachweis (POST формы)
    assert reverse("mbg_reports:work_completion_export") in content
    assert reverse("mbg_reports:performance_download", args=[documents_hub_setup["perf_artifact"].pk]) in content

    # 4. Промежуточный Zwischennachweis
    assert reverse("mbg_reports:multi_performance_export") in content
    assert reverse("mbg_reports:performance_exports", args=[documents_hub_setup["group_alpha"].pk]) in content

    # 5. JS скрипт и элементы селектора
    assert "mbg_reports/js/export_hub.js" in content
    assert 'id="custom-zwischen-form"' in content or 'data-action="toggle-picker"' in content
    assert 'id="custom-zwischen-picker"' in content


def test_documents_search_by_address_and_encode_pagination(documents_hub_setup, client):
    """Адрес ищется, а спецсимволы поиска не становятся параметрами страниц."""
    client.force_login(documents_hub_setup["admin"])
    response = client.get(reverse("mbg_reports:export_hub"), {"q": "Sonnenweg"})
    assert response.context["work_completion_groups"].paginator.count == 1
    response = client.get(
        reverse("mbg_reports:export_hub"),
        {"q": "Alpha & Beta", "page_weeks": "2", "page_completion": "3"},
    )
    assert response.context["weeks_pagination_params"] == "q=Alpha+%26+Beta&page_completion=1"
    assert response.context["completion_pagination_params"] == "q=Alpha+%26+Beta&page_weeks=1"
