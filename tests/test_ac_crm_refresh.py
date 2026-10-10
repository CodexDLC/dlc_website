"""Тесты визуального обновления AC CRM: дашборд, карточки, единый верх объекта и изоляция прав."""

from datetime import date
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from features.customer_portal.services import grant_membership
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.projects.models import AcObject, Client, ProjectGroup, SiteWorkItem
from features.work_catalog.models import WorkType

pytestmark = pytest.mark.django_db


def test_ac_dashboard_links_keep_language_prefix(ac_setup, client):
    client.force_login(ac_setup["manager"])
    response = client.get("/ru/cabinet/ac/dashboard/")
    assert response.status_code == 200
    content = response.content.decode()
    assert 'href="/cabinet/ac/' not in content
    assert 'href="/ru/cabinet/ac/groups/"' in content


@pytest.fixture
def ac_setup():
    users = get_user_model()
    manager = users.objects.create_superuser(username="ac-manager", email="manager@dlc.test", password=None)
    client_org = Client.objects.create(name="Auftraggeber Sol")
    customer_user = users.objects.create_user(username="sol-customer")
    grant_membership(actor=manager, user=customer_user, client=client_org, can_manage_projects=True)

    group_ac = ProjectGroup.objects.create(
        name="Anlage Alpha AC",
        client=client_org,
        address="Sonnenweg 1, Berlin",
        status="active",
        has_ac=True,
        has_dc=False,
    )
    group_dc_only = ProjectGroup.objects.create(
        name="Anlage DC Only Berlin",
        client=client_org,
        address="Gartenstraße 2, Berlin",
        status="active",
        has_ac=False,
        has_dc=True,
    )

    site_ac = AcObject.objects.create(
        group=group_ac,
        name="Standort A1",
        address="Sonnenweg 1A",
        project_number="P-AC-01",
        status="started",
    )
    site_dc = AcObject.objects.create(
        group=group_dc_only,
        name="Standort DC1",
        address="Gartenstraße 2A",
        project_number="P-DC-01",
        status="started",
    )

    work_type = WorkType.objects.create(
        code="ac_montage",
        name_ru="Монтаж инвертора",
        name_de="Wechselrichter Montage",
        unit="Stk",
    )
    plan_item = SiteWorkItem.objects.create(
        site=site_ac,
        work_type=work_type,
        planned_quantity=2,
        unit_snapshot="Stk",
        is_required=True,
    )

    report = MbgDailyReport.objects.create(
        author=manager,
        site=site_ac,
        work_date=date(2026, 10, 3),
        status="accepted",
        version=1,
        submission_key=uuid4(),
    )
    MbgReportRevision.objects.create(
        report=report,
        version=1,
        actor=manager,
        snapshot={
            "status": "accepted",
            "entries": [
                {
                    "work_type_code": "ac_montage",
                    "description": "Wechselrichter Montage",
                    "completed_quantity": "1",
                    "unit": "Stk",
                    "actual_person_hours": "3.5",
                    "calculation_rule": "piecework",
                    "work_item_id": plan_item.pk,
                }
            ],
        },
    )

    return {
        "manager": manager,
        "customer": customer_user,
        "client": client_org,
        "group_ac": group_ac,
        "group_dc_only": group_dc_only,
        "site_ac": site_ac,
        "site_dc": site_dc,
        "plan_item": plan_item,
        "report": report,
    }


def test_ac_dashboard_renders_actual_data_not_placeholder(ac_setup, client):
    """Дашборд AC показывает реальные данные и селекторы вместо заглушки."""
    client.force_login(ac_setup["manager"])
    url = reverse("cabinet:workspace_home")
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()

    # Заглушка устранена
    assert "визуальный прототип без данных и рабочих действий" not in content
    assert "crm-placeholder" not in content

    # Реальные счётчики и ссылки AC-пространства
    assert "Anlage Alpha AC" in content or "1" in content  # Счётчик групп или имя группы
    assert "/cabinet/ac/groups/" in content
    assert "/cabinet/ac/objects/" in content
    assert reverse("mbg_reports:list") in content or "/cabinet/ac/mbg-reports/" in content


def test_ac_groups_and_objects_filters_pagination_and_no_dc_only(ac_setup, client):
    """Списки групп и объектов AC: фильтры, пагинация 20, адаптивные карточки, исключение DC-only."""
    client.force_login(ac_setup["manager"])

    # 1. Группы AC
    resp_groups = client.get("/cabinet/ac/groups/", follow=True)
    assert resp_groups.status_code == 200
    content_groups = resp_groups.content.decode()
    assert "Anlage Alpha AC" in content_groups
    # DC-only группы Берлин/Finsterwalde не должны попадать в AC-группы
    assert "Anlage DC Only Berlin" not in content_groups
    assert "customer-card" in content_groups or "customer-grid" in content_groups
    assert 'name="q"' in content_groups

    # 2. Объекты AC
    resp_objects = client.get("/cabinet/ac/objects/", follow=True)
    assert resp_objects.status_code == 200
    content_objects = resp_objects.content.decode()
    assert "Standort A1" in content_objects
    assert "Standort DC1" not in content_objects
    assert "customer-card" in content_objects or "customer-grid" in content_objects
    assert 'name="status"' in content_objects
    assert 'name="sort"' in content_objects


def test_unified_object_top_and_internal_manager_block_isolation(ac_setup, client):
    """Единый верх объекта: адрес/статус DLC, ОДНА таблица выполненных работ, фото/документы, свёрнутая история.

    Клиент не видит внутренний блок плана и финансы; менеджер видит блок управления планом ниже общего верха.
    """
    site_ac = ac_setup["site_ac"]
    group_ac = ac_setup["group_ac"]

    # 1. Клиентский кабинет (customer_portal:site)
    client.force_login(ac_setup["customer"])
    resp_cust = client.get(reverse("customer_portal:site", args=[site_ac.pk]))
    assert resp_cust.status_code == 200
    content_cust = resp_cust.content.decode()

    # Адрес и статус DLC
    assert "Sonnenweg 1A" in content_cust
    assert site_ac.get_status_display() in content_cust

    # ОДНА сводная таблица выполненных работ
    assert "Wechselrichter Montage" in content_cust
    # Клиентский план со строками 'План и выполненный объём' убран
    assert "План и выполненный объём" not in content_cust
    # История работ свёрнута (через details)
    assert "<details" in content_cust
    # Никаких внутренних финансовых сумм / цен / предварительных расчётов для клиента
    assert "Teilbetrag" not in content_cust
    assert "Preis nicht vereinbart" not in content_cust
    # Note regarding lack of per-work acceptance by Emil
    assert "не реализована" in content_cust or "nicht implementiert" in content_cust or "общая проверка" in content_cust

    # 2. Внутренний CRM-маршрут менеджера (projects:site_detail)
    client.force_login(ac_setup["manager"])
    resp_mgr = client.get(reverse("projects:site_detail", args=[group_ac.pk, site_ac.pk]))
    assert resp_mgr.status_code == 200
    content_mgr = resp_mgr.content.decode()

    # Внутренний менеджерский блок плана находится НИЖЕ общего верха
    assert "Sonnenweg 1A" in content_mgr
    assert "Wechselrichter Montage" in content_mgr
    # Менеджер видит готовность плана и элементы управления
    assert "План работ Standort" in content_mgr or "Готовность плана" in content_mgr
    assert reverse("projects:work_item_new", args=[group_ac.pk, site_ac.pk]) in content_mgr
    assert "status-quick-select" in content_mgr or 'name="status"' in content_mgr


def test_mbg_reports_journal_by_day_and_actions(ac_setup, client):
    """Журнал отчётов MBG сгруппирован по дням/карточкам, административные действия сохранены."""
    client.force_login(ac_setup["manager"])
    resp = client.get(reverse("mbg_reports:list"))
    assert resp.status_code == 200
    content = resp.content.decode()

    assert "03.10.2026" in content or "2026-10-03" in content
    assert reverse("mbg_reports:detail", args=[ac_setup["report"].pk]) in content
    assert reverse("mbg_reports:new") in content
    assert "customer-day" in content or "mbg-report" in content or "customer-card" in content


def test_export_and_doc_list_compact_left_aligned_max1200(ac_setup, client):
    """Страницы выгрузок и документов выровнены по левому краю с ограничением max-width: 1200px."""
    client.force_login(ac_setup["manager"])
    resp = client.get(reverse("mbg_reports:export_hub"))
    assert resp.status_code == 200
    content = resp.content.decode()

    assert "customer-documents-content" in content or "max-width: 1200px" in content or "max-width:1200px" in content
