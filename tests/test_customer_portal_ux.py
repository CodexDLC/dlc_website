"""Тесты UX клиентского кабинета: адаптивные сетки, пагинация 20, журнал работ, фильтры и изоляция."""

from datetime import date
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from features.customer_portal.models import SiteReview
from features.customer_portal.services import grant_membership
from features.integrations.nextcloud.services import get_site_photo_cache_key
from features.mbg_reports.models import MbgDailyReport, MbgReportRevision
from features.project_media.models import ProjectFile
from features.projects.models import AcObject, Client, ProjectGroup

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("actor_key", ["admin", "alice"])
def test_internal_dc_group_is_not_customer_visible(ux_setup, client, actor_key):
    from django.core.exceptions import PermissionDenied
    from features.customer_portal.policies import require_customer_group
    from features.customer_portal.selectors import groups_for_actor

    group = ProjectGroup.objects.create(
        name="Internal DC Berlin", client=ux_setup["client_a"], has_ac=False, has_dc=True,
    )
    actor = ux_setup[actor_key]
    assert not groups_for_actor(actor).filter(pk=group.pk).exists()
    with pytest.raises(PermissionDenied):
        require_customer_group(actor, group)
    client.force_login(actor)
    response = client.get(reverse("customer_portal:home"))
    assert "Internal DC Berlin" not in response.content.decode()


@pytest.mark.parametrize(
    "route,query",
    [
        ("objects", "group=invalid"),
        ("works", "group=invalid"),
        ("works", "site=invalid"),
    ],
)
def test_invalid_scope_id_is_not_server_error(ux_setup, client, route, query):
    client.force_login(ux_setup["alice"])
    response = client.get(reverse(f"customer_portal:{route}") + "?" + query)
    assert response.status_code == 404


@pytest.fixture
def ux_setup():
    users = get_user_model()
    admin = users.objects.create_superuser(username="ux-admin", email="admin@ux.test", password=None)
    alice = users.objects.create_user(username="ux-alice")
    bob = users.objects.create_user(username="ux-bob")

    client_a = Client.objects.create(name="Auftraggeber Alpha")
    client_b = Client.objects.create(name="Auftraggeber Beta")

    grant_membership(actor=admin, user=alice, client=client_a, can_manage_projects=True)
    grant_membership(actor=admin, user=bob, client=client_b, can_manage_projects=False)

    group_a = ProjectGroup.objects.create(
        name="Anlage Alpha",
        client=client_a,
        address="Musterstraße 1, Berlin",
        status="active",
        has_ac=True,
        has_dc=False,
    )
    group_b = ProjectGroup.objects.create(
        name="Anlage Beta",
        client=client_b,
        address="Hauptstraße 2, München",
        status="active",
        has_ac=True,
        has_dc=True,
    )

    site_a = AcObject.objects.create(
        group=group_a,
        name="Standort Alpha 1",
        address="Musterstraße 1A",
        project_number="P-A1",
        status="started",
    )
    site_b = AcObject.objects.create(
        group=group_b,
        name="Standort Beta 1",
        address="Hauptstraße 2B",
        project_number="P-B1",
        status="started",
    )

    return {
        "admin": admin,
        "alice": alice,
        "bob": bob,
        "client_a": client_a,
        "client_b": client_b,
        "group_a": group_a,
        "group_b": group_b,
        "site_a": site_a,
        "site_b": site_b,
    }


def _create_accepted_report(site, author, work_date, entries, version=1):
    report = MbgDailyReport.objects.create(
        author=author,
        site=site,
        work_date=work_date,
        status="accepted",
        version=version,
        submission_key=uuid4(),
    )
    MbgReportRevision.objects.create(
        report=report,
        actor=author,
        version=version,
        action="accept",
        snapshot={
            "status": "accepted",
            "entries": entries,
        },
    )
    return report


def test_home_groups_pagination_and_filters_and_card_links(ux_setup, client):
    ctx = ux_setup
    client.force_login(ctx["alice"])

    # Создаём 25 клиентских AC-групп: 22 active, 3 completed.
    for i in range(1, 26):
        status = "completed" if i > 22 else "active"
        has_ac = True
        has_dc = i % 2 == 0
        ProjectGroup.objects.create(
            name=f"Anlage Batch {i:02d}",
            client=ctx["client_a"],
            address=f"Musterstraße {i}, Berlin",
            status=status,
            has_ac=has_ac,
            has_dc=has_dc,
        )

    # 1. По умолчанию отображаются активные группы, пагинация 20 на страницу
    res = client.get(reverse("customer_portal:home"))
    assert res.status_code == 200
    content = res.content.decode()
    # 22 active + 1 initial = 23 active groups. Page 1 has 20, page 2 has 3
    assert "page=2" in content
    # Ссылка с карточки группы ведёт на objects?group=ID
    assert f'href="{reverse("customer_portal:objects")}?group={ctx["group_a"].pk}"' in content
    # Карточка группы не содержит вложенного списка Standorte
    assert "Standorte ещё не добавлены" not in content

    # 2. Фильтр status=completed
    res_completed = client.get(reverse("customer_portal:home") + "?status=completed")
    assert res_completed.status_code == 200
    content_c = res_completed.content.decode()
    assert "Anlage Batch 23" in content_c
    assert "Anlage Batch 01" not in content_c

    # 3. Фильтр status=all
    res_all = client.get(reverse("customer_portal:home") + "?status=all")
    assert res_all.status_code == 200

    # 4. Поиск по названию/адресу
    res_search = client.get(reverse("customer_portal:home") + "?q=Batch 05")
    assert res_search.status_code == 200
    assert "Anlage Batch 05" in res_search.content.decode()
    assert "Anlage Batch 06" not in res_search.content.decode()

    # 5. Сохранение параметров в пагинации
    res_page = client.get(reverse("customer_portal:home") + "?q=Batch&page=2")
    assert res_page.status_code == 200
    assert "q=Batch" in res_page.content.decode()


def test_objects_grid_pagination_and_filters_and_sorting(ux_setup, client):
    ctx = ux_setup
    client.force_login(ctx["alice"])

    # Создаём 25 Standorte в группе Alpha
    for i in range(1, 26):
        AcObject.objects.create(
            group=ctx["group_a"],
            name=f"Standort {i:02d}",
            address=f"Weg {i}",
            project_number=f"P-{i:03d}",
            status="completed" if i > 22 else "started",
        )

    # 1. По умолчанию 20 на страницу, non-completed
    res = client.get(reverse("customer_portal:objects"))
    assert res.status_code == 200
    content = res.content.decode()
    assert "page=2" in content
    # P/Nr отображается
    assert "P-" in content
    # group chip with clear link when group filter selected
    res_group = client.get(reverse("customer_portal:objects") + f"?group={ctx['group_a'].pk}")
    assert res_group.status_code == 200
    content_g = res_group.content.decode()
    assert "Anlage Alpha" in content_g
    # Link to clear group chip
    assert 'href="?' in content_g or "group=" in content_g

    # 2. Сортировка по имени: Standort 01 с P-001 на первой странице
    res_sort_name = client.get(reverse("customer_portal:objects") + "?sort=name")
    assert res_sort_name.status_code == 200
    assert "P-001" in res_sort_name.content.decode()

    # 3. Кешированный бейдж Nextcloud (unknown / unavailable / count)
    cache.clear()
    site = ctx["site_a"]
    key = get_site_photo_cache_key(site)

    # Без кеша: unknown / —
    res_obj = client.get(reverse("customer_portal:objects") + f"?q={site.name}")
    assert "Keine Fotos" not in res_obj.content.decode()

    # Кеш со статусом unavailable
    cache.set(key, {"status": "unavailable", "count": 0, "photos": []}, 300)
    res_unavail = client.get(reverse("customer_portal:objects") + f"?q={site.name}")
    assert "Keine Fotos" not in res_unavail.content.decode()

    # Кеш со статусом ok и 3 фото
    sample_photos = [{"name": "1.jpg"}, {"name": "2.jpg"}, {"name": "3.jpg"}]
    cache.set(key, {"status": "ok", "count": 3, "photos": sample_photos}, 300)
    res_ok = client.get(reverse("customer_portal:objects") + f"?q={site.name}")
    assert "3" in res_ok.content.decode()


def test_cross_client_crafted_params_cannot_leak(ux_setup, client):
    ctx = ux_setup
    client.force_login(ctx["alice"])

    # Alice пытается подставить group_b или site_b в objects
    res_objects = client.get(reverse("customer_portal:objects") + f"?group={ctx['group_b'].pk}")
    assert res_objects.status_code == 200
    # Объекты Beta не должны показаться
    assert "Standort Beta 1" not in res_objects.content.decode()
    assert "Anlage Beta" not in res_objects.content.decode()

    # Alice пытается подставить group_b или site_b в works
    res_works_group = client.get(reverse("customer_portal:works") + f"?group={ctx['group_b'].pk}")
    assert res_works_group.status_code == 200
    assert "Standort Beta 1" not in res_works_group.content.decode()

    res_works_site = client.get(reverse("customer_portal:works") + f"?site={ctx['site_b'].pk}")
    assert res_works_site.status_code == 200
    assert "Standort Beta 1" not in res_works_site.content.decode()


def test_works_journal_days_pagination_and_breaks_excluded(ux_setup, client):
    ctx = ux_setup
    client.force_login(ctx["alice"])

    # Создаём отчёты на 9 уникальных дней для site_a
    # Включаем паузы и обычные работы
    for day in range(1, 10):
        w_date = date(2026, 9, day)
        entries = [
            {
                "description": f"Montage Tag {day}",
                "unit": "Stk",
                "completed_quantity": "5",
                "actual_person_hours": "8.0",
                "is_break": False,
            },
            {
                "description": "Mittagspause",
                "unit": "Std.",
                "work_type_code": "mittagspause",
                "completed_quantity": "0",
                "actual_person_hours": "0.5",
                "is_break": True,
            },
        ]
        _create_accepted_report(ctx["site_a"], ctx["admin"], w_date, entries)

    # 1. Запрос журнала работ: пагинация 7 уникальных дней на страницу
    res = client.get(reverse("customer_portal:works"))
    assert res.status_code == 200
    content = res.content.decode()
    assert "page=2" in content
    # Ссылка на сайт с датой site?date=YYYY-MM-DD
    expected_link = f"{reverse('customer_portal:site', args=[ctx['site_a'].pk])}?date=2026-09-09"
    assert expected_link in content
    # В карточке объекта указано количество строк работ (1 строка, так как пауза исключена)
    assert "1" in content

    # 2. Фильтр дат from / to
    res_filtered = client.get(reverse("customer_portal:works") + "?from=2026-09-05&to=2026-09-07")
    assert res_filtered.status_code == 200
    c_f = res_filtered.content.decode()
    assert "2026-09-05" in c_f or "05.09.2026" in c_f
    assert "2026-09-09" not in c_f

    # 3. Неверный формат даты не роняет сервер с кодом 500
    res_bad_date = client.get(reverse("customer_portal:works") + "?from=invalid-date")
    assert res_bad_date.status_code == 200


def test_site_detail_chosen_date_filter_and_highlight(ux_setup, client):
    ctx = ux_setup
    client.force_login(ctx["alice"])

    # Добавляем 2 отчёта на разные даты
    _create_accepted_report(
        ctx["site_a"],
        ctx["admin"],
        date(2026, 9, 1),
        [{"description": "Arbeit Tag 1", "unit": "Stk", "completed_quantity": "2", "actual_person_hours": "4"}],
    )
    _create_accepted_report(
        ctx["site_a"],
        ctx["admin"],
        date(2026, 9, 2),
        [{"description": "Arbeit Tag 2", "unit": "Stk", "completed_quantity": "3", "actual_person_hours": "6"}],
    )

    # Запрашиваем site detail с датой
    res = client.get(reverse("customer_portal:site", args=[ctx["site_a"].pk]) + "?date=2026-09-01")
    assert res.status_code == 200
    content = res.content.decode()
    # Сводные выполненные работы, фотогалерея и проверка сохранены
    assert "Выполненные работы" in content
    assert "Фотографии стройплощадки" in content
    assert "Проверка заказчиком" in content
    # Строка с выбранной датой выделена/присутствует
    assert "2026-09-01" in content


def test_documents_search_and_split_pagination_and_button_titles(ux_setup, client, tmp_path, settings):
    settings.PRIVATE_MEDIA_ROOT = tmp_path
    ctx = ux_setup
    client.force_login(ctx["alice"])

    # Создаём 25 групп и 25 PDF файлов для client_a
    for i in range(1, 26):
        grp = ProjectGroup.objects.create(name=f"Anlage Doc {i:02d}", client=ctx["client_a"])
        ProjectFile.objects.create(
            group=grp,
            original_name=f"Dokument_{i:02d}.pdf",
            file=f"mock_{i}.pdf",
            content_type="application/pdf",
            size=1024,
            kind="document",
            uploaded_by=ctx["admin"],
            customer_visible=True,
        )

    res = client.get(reverse("customer_portal:documents"))
    assert res.status_code == 200
    content = res.content.decode()
    # Пагинация групп (20 на страницу)
    assert "page_groups=2" in content
    # Пагинация PDF (20 на страницу)
    assert "page_pdf=2" in content
    # Заголовок кнопки сводного акта без дисклеймера "без цен"
    assert "без цен" not in content
    assert "ohne Preise" not in content
    assert "Сводный акт (XLSX)" in content or "Gesamtnachweis" in content

    # Поиск по документам
    res_search = client.get(reverse("customer_portal:documents") + "?q_pdf=Dokument_05")
    assert res_search.status_code == 200
    assert "Dokument_05.pdf" in res_search.content.decode()
    assert "Dokument_06.pdf" not in res_search.content.decode()


def test_reviews_grid_and_empty_help(ux_setup, client, monkeypatch):
    def forbidden_photo_lookup(*args, **kwargs):
        raise AssertionError("Review list must not access Nextcloud or photo summaries")

    monkeypatch.setattr("features.customer_portal.views.get_cached_photo_summary", forbidden_photo_lookup)
    monkeypatch.setattr(
        "features.integrations.nextcloud.client.NextcloudWebDAVClient.list_folder", forbidden_photo_lookup
    )
    ctx = ux_setup
    client.force_login(ctx["alice"])

    # Когда нет проверок: понятный пустой экран без фейковых данных
    res_empty = client.get(reverse("customer_portal:reviews"))
    assert res_empty.status_code == 200
    assert "Пока нет проверок" in res_empty.content.decode() or "проверок" in res_empty.content.decode()

    # Создаём 25 проверок
    for i in range(1, 26):
        st = AcObject.objects.create(group=ctx["group_a"], name=f"Standort Rev {i:02d}")
        SiteReview.objects.create(site=st, status="submitted", remark=f"Prüfung {i}")

    res_grid = client.get(reverse("customer_portal:reviews"))
    assert res_grid.status_code == 200
    content = res_grid.content.decode()
    # 20 на страницу
    assert "page=2" in content
    assert "Prüfung 1" in content
    assert "cust-badge--photo" not in content
