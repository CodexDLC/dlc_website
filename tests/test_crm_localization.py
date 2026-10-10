"""Основные новые экраны и формы переводятся в немецкой версии."""

import re

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.translation import override
from features.management_reports.forms import MonthForm
from features.mbg_reports.forms import EntryForm, ReportForm


def test_german_form_labels():
    with override("de"):
        assert ReportForm().fields["work_date"].label == "Datum"
        assert EntryForm().fields["participants"].label == "Ausführende Mitarbeiter"
        assert MonthForm().fields["month"].label == "Monat"
    with override("ru"):
        assert ReportForm().fields["work_date"].label == "Дата"


def test_hour_totals_use_active_language():
    from features.internal_time.calculations import format_minutes

    with override("de"):
        assert format_minutes(90) == "1 Std. 30 Min."
    with override("ru"):
        assert format_minutes(90) == "1 ч 30 мин"


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["de", "ru"])
@pytest.mark.parametrize(
    "route",
    [
        "cabinet:workspace_home",
        "projects:list",
        "projects:new",
        "internal_time:list",
        "internal_time:new",
        "crews:list",
        "customer_portal:home",
        "customer_portal:account",
    ],
)
def test_complete_cabinet_pages_use_selected_language(client, language, route):
    user = get_user_model().objects.create_superuser(username="locale-owner", email="owner@example.test", password=None)
    client.force_login(user)
    with override(language):
        response = client.get(reverse(route))
    assert response.status_code == 200
    document = response.content.decode()
    document = re.sub(r"<(script|style)\b.*?</\1>|<!--.*?-->", "", document, flags=re.S)
    visible = strip_tags(document)
    expected_heading = {
        "cabinet:workspace_home": ("AC-Bereichsübersicht", "Обзор направления AC"),
        "projects:list": ("Projekte", "Проекты"),
        "projects:new": ("Projektname", "Название проекта"),
        "internal_time:list": ("Interne Berichte", "Внутренние отчёты"),
        "internal_time:new": ("Teambericht", "Отчёт команды"),
        "crews:list": ("Teams", "Команды"),
        "customer_portal:home": ("Meine Übersicht", "Мой обзор"),
        "customer_portal:account": ("Mein Konto", "Мой аккаунт"),
    }
    assert expected_heading[route][language == "ru"] in visible
    if language == "de":
        assert not re.search("[А-Яа-я]", visible), re.findall(r"[^\n]*[А-Яа-я][^\n]*", visible)
    else:
        assert re.search("[А-Яа-я]", visible)
        assert "Sign Out" not in visible
        assert "Open navigation" not in visible


def test_form_unit_translation_preserves_financial_snapshot_units():
    from features.work_catalog.forms import WorkTypeForm
    from features.work_catalog.models import WorkType

    with override("ru"):
        work = WorkType(unit=WorkType.Unit.FLAT)
        # The settlement projection recognizes this canonical stored unit.
        assert work.get_unit_display() == "psch."
        assert dict(WorkTypeForm().fields["unit"].choices)[WorkType.Unit.FLAT] == "пауш."


@pytest.mark.parametrize(
    ("language", "count", "expected"),
    [
        ("de", 1, "1 Foto vorhanden"),
        ("de", 2, "2 Fotos vorhanden"),
        ("de", 5, "5 Fotos vorhanden"),
        ("ru", 1, "1 фотография"),
        ("ru", 2, "2 фотографии"),
        ("ru", 5, "5 фотографий"),
    ],
)
def test_site_photo_counter_uses_language_plural_forms(language, count, expected):
    from types import SimpleNamespace

    from django.template.loader import render_to_string

    group = SimpleNamespace(pk=1, name="Test")
    site = SimpleNamespace(pk=1, group_id=1, name="Test", address="", project_number="")
    summary = SimpleNamespace(count=count, status="ok", is_available=True)
    with override(language):
        html = render_to_string(
            "projects/includes/_object_common_top.html",
            {"site": site, "group": group, "photo_summary": summary},
        )
    assert expected in strip_tags(html)
    assert "фотографияs" not in html
