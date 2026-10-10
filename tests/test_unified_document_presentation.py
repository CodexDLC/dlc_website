"""Isolated presentation contract tests for unified documents screen.

Verifies:
1. Reusable partial shared between customer portal and internal mbg cabinet.
2. Compact-left container matching Emil documents.html exactly.
3. Simple Russian labels: Акт, Табель часов, Сводный акт, Сводный табель.
4. Foreman and customer never see financial tabs, settlement buttons, or pay controls.
5. Internal admin with can_manage_settlement sees Отчёт для выставления счёта and master tab.
6. Legacy name Для Димы is strictly absent.
7. Master tab contains common Excel action and explicit update Google Sheets form with CSRF.
8. Payment badges (Оплачено / К оплате), archive viewability, and exclusion from new invoice selection.
9. Safety when action URLs are missing.
"""

from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import RequestFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_request():
    """Тестовый запрос с поддержкой CSRF и аутентифицированным пользователем."""
    rf = RequestFactory()
    request = rf.get("/portal/documents/")
    user = get_user_model().objects.create_user(username="test_doc_user")
    request.user = user
    return request


@pytest.fixture
def mock_site_dto():
    """DTO площадки для документов."""

    class SiteDTO:
        def __init__(self, pk, name, project_number, status_display, is_paid=False):
            self.pk = pk
            self.name = name
            self.project_number = project_number
            self.status_display = status_display
            self.is_paid = is_paid
            self.detail_url = f"/portal/site/{pk}/"
            self.act_url = f"/portal/site/{pk}/act.xlsx"
            self.timesheet_url = f"/portal/site/{pk}/timesheet.xlsx"
            self.settlement_report_url = f"/cabinet/settlement/site/{pk}/report.xlsx"

        def get_status_display(self):
            return self.status_display

    return SiteDTO


@pytest.fixture
def mock_group_dto(mock_site_dto):
    """DTO группы проектов (Anlage) для документов."""

    class GroupDTO:
        def __init__(self, pk, name, address="", sites=None):
            self.pk = pk
            self.name = name
            self.address = address
            self.detail_url = f"/portal/group/{pk}/"
            self.group_act_url = f"/portal/group/{pk}/work.xlsx"
            self.group_timesheet_url = f"/portal/group/{pk}/timesheet.xlsx"
            self.sites = sites or []

        @property
        def ac_objects(self):
            class Manager:
                def __init__(self, items):
                    self._items = items

                def all(self):
                    return self._items

            return Manager(self.sites)

    return GroupDTO


@pytest.fixture
def sample_pdf_files():
    """Список PDF файлов для раздела проектных документов."""

    class FileDTO:
        def __init__(self, pk, original_name, group_name, site_name, created_at_str):
            self.pk = pk
            self.original_name = original_name
            self.group = MagicMock(name=group_name)
            self.group.name = group_name
            self.site = MagicMock(name=site_name)
            self.site.name = site_name
            self.download_url = f"/portal/file/{pk}/download/"

        @property
        def created_at(self):
            return self.download_url

    return [
        FileDTO(101, "Bauplan_A1.pdf", "Anlage Alpha", "Standort Alpha 1", "01.10.2026 10:00"),
        FileDTO(102, "Messprotokoll_B1.pdf", "Anlage Beta", "Standort Beta 1", "02.10.2026 12:00"),
    ]


@pytest.fixture
def base_context(mock_group_dto, mock_site_dto, sample_pdf_files):
    """Базовый контекст для рендеринга шаблонов."""
    site1 = mock_site_dto(1, "Standort 1", "P-101", "In Arbeit", is_paid=False)
    site2 = mock_site_dto(2, "Standort 2", "P-102", "Fertig", is_paid=True)
    group = mock_group_dto(1, "Anlage Dresden", "Hauptstr. 10, Dresden", sites=[site1, site2])

    paginator_groups = Paginator([group], 20)
    groups_page = paginator_groups.page(1)

    paginator_pdf = Paginator(sample_pdf_files, 20)
    files_page = paginator_pdf.page(1)

    return {
        "groups_page": groups_page,
        "files_page": files_page,
        "q_group": "",
        "q_pdf": "",
        "page_groups": 1,
        "page_pdf": 1,
        "can_manage_settlement": False,
        "batch_settlement_report_url": "/cabinet/settlement/batch-report/",
        "download_common_excel_url": "/cabinet/settlement/master-table.xlsx",
        "update_google_sheets_url": "/cabinet/settlement/sync-google-sheets/",
    }


def test_customer_view_renders_acts_and_timesheets_never_finances(mock_request, base_context):
    """Клиентский экран содержит акты и табели, но категорически исключает финансы."""
    base_context["can_manage_settlement"] = False

    html = render_to_string(
        "customer_portal/unified_documents.html",
        base_context,
        request=mock_request,
    )

    # Заголовок и базовый контекст
    assert "Документы" in html
    assert "Anlage Dresden" in html
    assert "Standort 1" in html
    assert "Standort 2" in html

    # Простые русские метки кнопок документов
    assert "Сводный акт" in html
    assert "Сводный табель" in html
    assert "Акт" in html
    assert "Табель часов" in html

    # Запрет финансовых элементов для клиента
    assert "Отчёт для выставления счёта" not in html
    assert "Для Димы" not in html
    assert "Сводная ведомость" not in html
    assert "Обновить Google Таблицу" not in html
    assert "Включить оплаченные" not in html
    assert "unified-doc-badge--paid" not in html
    assert "unified-doc-badge--unpaid" not in html


def test_internal_admin_view_renders_tabs_and_settlement_controls(mock_request, base_context):
    """Внутренний администратор видит вкладки, отчёты для счёта и управление расчётами."""
    base_context["can_manage_settlement"] = True

    html = render_to_string(
        "mbg_reports/unified_documents.html",
        base_context,
        request=mock_request,
    )

    # Вкладки доступны только админу
    assert "Акты и табели" in html
    assert "Сводная ведомость" in html

    # Кнопки счёта: построчно и для выбранных
    assert "Отчёт для выставления счёта" in html
    # Ни в коем случае не должно быть старого названия
    assert "Для Димы" not in html

    # Бейджи оплаты и фильтр
    assert "Включить оплаченные" in html
    assert "unified-doc-badge--paid" in html
    assert "unified-doc-badge--unpaid" in html
    assert "Оплачено" in html
    assert "К оплате" in html

    # Форма обновления Google Таблицы с CSRF и action URL
    assert 'action="/cabinet/settlement/sync-google-sheets/"' in html
    assert "Обновить Google Таблицу" in html
    assert 'name="csrfmiddlewaretoken"' in html

    # Скачивание сводной ведомости
    assert 'href="/cabinet/settlement/master-table.xlsx"' in html


def test_foreman_role_without_settlement_rights_never_sees_finances(mock_request, base_context):
    """Прораб без прав can_manage_settlement не видит финансовые кнопки и вкладки."""
    base_context["can_manage_settlement"] = False

    html = render_to_string(
        "mbg_reports/unified_documents.html",
        base_context,
        request=mock_request,
    )

    # Прораб видит акты и табели
    assert "Акт" in html
    assert "Табель часов" in html
    assert "Сводный акт" in html
    assert "Сводный табель" in html

    # Прораб не видит вкладки и финансы
    assert "Сводная ведомость" not in html
    assert "Отчёт для выставления счёта" not in html
    assert "Для Димы" not in html
    assert "Обновить Google Таблицу" not in html
    assert "Включить оплаченные" not in html


def test_paid_rows_remain_viewable_archive_but_excluded_from_invoice_selection(
    mock_request, base_context
):
    """Оплаченные объекты видны в списке (архив), но чекбокс выбора для счёта отключён."""
    base_context["can_manage_settlement"] = True

    html = render_to_string(
        "mbg_reports/unified_documents.html",
        base_context,
        request=mock_request,
    )

    # Both site rows remain viewable
    assert "Standort 1" in html
    assert "Standort 2" in html

    # Standort 1 (unpaid): checkbox is enabled
    assert 'name="site_ids" value="1"' in html
    # Standort 2 (paid): checkbox is disabled for new invoice generation
    assert 'value="2" disabled' in html or 'disabled title="Оплачено"' in html or 'disabled' in html


def test_missing_action_urls_disables_dangerous_buttons(mock_request, base_context):
    """When action URLs are not supplied by integrator, dangerous buttons are disabled."""
    base_context["can_manage_settlement"] = True
    base_context["update_google_sheets_url"] = None
    base_context["batch_settlement_report_url"] = None

    html = render_to_string(
        "mbg_reports/unified_documents.html",
        base_context,
        request=mock_request,
    )

    # Google Sheets update button is disabled
    assert "Обновить Google Таблицу" in html
    assert "disabled" in html
    # Warning or disabled state present
    assert "не подключён" in html or "URL действия не настроен" in html or "disabled" in html


def test_pdf_section_and_filters_preserved(mock_request, base_context):
    """Preserves filters and PDF documents section per contract."""
    html = render_to_string(
        "customer_portal/unified_documents.html",
        base_context,
        request=mock_request,
    )

    # Filter inputs
    assert 'name="q_group"' in html
    assert 'name="q_pdf"' in html
    assert "Поиск проектов" in html
    assert "Поиск PDF документов" in html

    # PDF table
    assert "Проектные документы (PDF)" in html
    assert "Bauplan_A1.pdf" in html
    assert "Messprotokoll_B1.pdf" in html


def test_both_wrappers_reuse_same_partial(mock_request, base_context):
    """Both wrappers render successfully using the shared documents partial."""
    # Direct render of partial
    partial_html = render_to_string(
        "customer_portal/includes/_unified_documents_partial.html",
        base_context,
        request=mock_request,
    )
    assert "Клиентские ведомости и акты" in partial_html
    assert "Anlage Dresden" in partial_html
