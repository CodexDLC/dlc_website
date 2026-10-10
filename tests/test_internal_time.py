"""Проверки браузерного сценария, прав, времени и переходов состояний."""

from datetime import time, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone
from features.crews.services import save_team
from features.internal_time.models import TeamReport, WorkType
from features.internal_time.policies import can_edit
from features.internal_time.selectors import report_summary
from features.internal_time.services import review_report, save_report
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee

pytestmark = pytest.mark.django_db


def test_vorarbeiter_replaces_legacy_master_role():
    assert "is_master" not in {field.name for field in Employee._meta.fields}
    from django.apps import apps
    assert "ProjectAssignment" not in {model.__name__ for model in apps.get_app_config("projects").get_models()}


@pytest.fixture
def actors():
    User = get_user_model()
    admin = User.objects.create_user(username="owner", is_staff=True, is_superuser=True)
    master = User.objects.create_user(username="master")
    second = User.objects.create_user(username="second")
    worker = Employee.objects.create(
        first_name="Dmytro", last_name="Sukhovyi", user=master, is_foreman=True, has_ac_access=True
    )
    other = Employee.objects.create(first_name="Mykhailo", last_name="Abrasov")
    Employee.objects.create(first_name="Second", last_name="Foreman", user=second, is_foreman=True, has_ac_access=True)
    group = ProjectGroup.objects.create(name="Berlin 38, 40, 42", responsible=admin)
    return admin, master, second, worker, other, group


def payload(group, **changes):
    data = dict(
        project_group=group,
        direction="ac",
        work_date=timezone.localdate(),
        starts_at=time(7),
        ends_at=time(18),
        lunch_minutes=30,
        work_description="",
        note="",
        submission_key=uuid4(),
    )
    data.update(changes)
    return data


def participant(employee, deduction=0):
    return {"employee": employee, "deduction_minutes": deduction}


def posted(group, worker, **changes):
    data = {
        "project_group": str(group.pk),
        "direction": "ac",
        "work_date": str(timezone.localdate()),
        "starts_at": "07:00",
        "ends_at": "18:00",
        "lunch_minutes": "30",
        "work_description": "",
        "note": "",
        "version": "",
        "submission_key": str(uuid4()),
        "members-TOTAL_FORMS": "1",
        "members-INITIAL_FORMS": "0",
        "members-MIN_NUM_FORMS": "1",
        "members-MAX_NUM_FORMS": "100",
        "members-0-employee": str(worker.pk),
        "members-0-deduction_minutes": "0",
        "action": "submit",
    }
    data.update(changes)
    return data


def test_paid_lunch_and_individual_deduction(actors):
    _, master, _, worker, other, group = actors
    report = save_report(
        actor=master, data=payload(group), participants=[participant(worker), participant(other, 60)], submit=True
    )
    summary = report_summary(report)
    assert summary["base"] == "11 ч 00 мин"
    assert summary["total"] == "21 ч 00 мин"
    assert len(summary["members"]) == 2
    assert report.revisions.count() == 1
    assert report.status == "submitted"


def test_internal_report_starts_only_anlage_direction(actors):
    _, master, _, worker, _, group = actors
    site = AcObject.objects.create(group=group, name="Haus 42")

    save_report(actor=master, data=payload(group), participants=[participant(worker)])

    group.refresh_from_db()
    site.refresh_from_db()
    assert group.ac_status == "started"
    assert group.dc_status == "not_started"
    assert site.status == "not_started"


@pytest.mark.parametrize("minutes", [-1, 660, 900])
def test_invalid_deduction_rolls_back(actors, minutes):
    _, master, _, worker, _, group = actors
    with pytest.raises(ValidationError):
        save_report(actor=master, data=payload(group), participants=[participant(worker, minutes)])
    assert TeamReport.objects.count() == 0


def test_duplicate_employee_and_overlap(actors):
    _, master, second, worker, _, group = actors
    with pytest.raises(ValidationError):
        save_report(actor=master, data=payload(group), participants=[participant(worker), participant(worker)])
    save_report(actor=master, data=payload(group), participants=[participant(worker)])
    with pytest.raises(ValidationError):
        save_report(actor=second, data=payload(group, starts_at=time(10)), participants=[participant(worker, 60)])
    save_report(
        actor=second, data=payload(group, starts_at=time(18), ends_at=time(19)), participants=[participant(worker)]
    )
    assert TeamReport.objects.count() == 2


def test_lifecycle_and_edit_limits(actors):
    admin, master, second, worker, _, group = actors
    report = save_report(actor=master, data=payload(group), participants=[participant(worker)], submit=True)
    assert can_edit(master, report)
    assert not can_edit(second, report)
    report = review_report(actor=admin, report_id=report.pk, decision="accept", version=1)
    assert not can_edit(master, report)
    with pytest.raises(PermissionDenied):
        save_report(
            actor=master, report_id=report.pk, version=2, data=payload(group), participants=[participant(worker)]
        )
    with pytest.raises(ValidationError):
        save_report(
            actor=admin, report_id=report.pk, version=2, data=payload(group), participants=[participant(worker)]
        )
    changed = save_report(
        actor=admin,
        report_id=report.pk,
        version=2,
        data=payload(group),
        participants=[participant(worker, 60)],
        reason="Исправлено по бумажному листу",
    )
    assert changed.status == "accepted"
    assert changed.revisions.first().reason
    changed.status = "returned"
    changed.submitted_at = timezone.now() - timedelta(days=8)
    changed.save()
    assert not can_edit(master, changed)


def test_return_resubmit_and_stale_version(actors):
    admin, master, _, worker, _, group = actors
    report = save_report(actor=master, data=payload(group), participants=[participant(worker)], submit=True)
    with pytest.raises(ValidationError):
        review_report(actor=admin, report_id=report.pk, version=1, decision="return")
    report = review_report(actor=admin, report_id=report.pk, version=1, decision="return", reason="Проверь время")
    with pytest.raises(ValidationError):
        save_report(
            actor=master, report_id=report.pk, version=1, data=payload(group), participants=[participant(worker)]
        )
    original_submission = report.submitted_at
    report = save_report(
        actor=master,
        report_id=report.pk,
        version=2,
        data=payload(group),
        participants=[participant(worker)],
        submit=True,
    )
    assert report.status == "submitted"
    assert report.submitted_at == original_submission


def test_idempotent_submission_and_direction_access(actors):
    _, master, second, worker, _, group = actors
    data = payload(group)
    first = save_report(actor=master, data=data, participants=[participant(worker)], submit=True)
    again = save_report(actor=master, data=data, participants=[participant(worker)], submit=True)
    assert first.pk == again.pk
    assert TeamReport.objects.count() == 1
    with pytest.raises(PermissionDenied):
        save_report(actor=second, data=data, participants=[participant(worker)])
    with pytest.raises(PermissionDenied):
        save_report(actor=master, data=payload(group, direction="dc"), participants=[participant(worker)])


def test_team_snapshot_independent(actors):
    _, master, _, worker, other, group = actors
    team = save_team(actor=master, name="Команда 1", owner=worker, members=[worker, other])
    report = save_report(actor=master, data=payload(group), participants=[participant(worker), participant(other)])
    save_team(actor=master, name="Команда 1", owner=worker, members=[worker], team_id=team.pk)
    assert report.participants.count() == 2


def test_browser_pages_and_htmx_submit(actors, client):
    admin, master, second, worker, _, group = actors
    client.force_login(master)
    for route in ("internal_time:list", "internal_time:new", "crews:list"):
        response = client.get(reverse(route))
        assert response.status_code == 200
    response = client.post(reverse("internal_time:new"), posted(group, worker), HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert response.headers["HX-Redirect"]
    detail = client.get(response.headers["HX-Redirect"])
    assert detail.status_code == 200
    assert "11 ч 00 мин" in detail.content.decode()
    report = TeamReport.objects.get()
    client.force_login(second)
    assert client.get(reverse("internal_time:detail", args=[report.pk])).status_code == 404
    assert (
        client.post(reverse("internal_time:review", args=[report.pk]), {"decision": "accept", "version": 1}).status_code
        == 404
    )
    client.force_login(admin)
    assert client.get(reverse("internal_time:list")).status_code == 200
    response = client.post(reverse("internal_time:review", args=[report.pk]), {"decision": "accept", "version": 1})
    assert response.status_code == 302
    report.refresh_from_db()
    assert report.status == "accepted"


def test_staff_actions_stay_inside_crm(actors, client):
    admin, _, _, _, _, _ = actors
    client.force_login(admin)

    reports_html = client.get(reverse("internal_time:list")).content.decode()
    teams_html = client.get(reverse("crews:list")).content.decode()
    admin_url = reverse("admin:staff_employee_changelist")

    assert reverse("staff_employee_new") in reports_html
    assert reverse("staff_employees") in teams_html
    assert admin_url not in reports_html
    assert admin_url not in teams_html


def test_htmx_rows_preserve_form_and_do_not_save(actors, client):
    _, master, _, worker, other, group = actors
    client.force_login(master)
    response = client.post(reverse("internal_time:new"), posted(group, worker, action="add"), HTTP_HX_REQUEST="true")
    content = response.content.decode()
    assert response.status_code == 200
    assert 'name="members-1-employee"' in content
    assert "<html" not in content
    assert TeamReport.objects.count() == 0
    team = save_team(actor=master, name="Тест", owner=worker, members=[worker, other])
    response = client.post(
        reverse("internal_time:new"), posted(group, worker, action="team", team=str(team.pk)), HTTP_HX_REQUEST="true"
    )
    assert 'name="members-1-employee"' in response.content.decode()


def test_validation_errors_remain_in_editor_and_new_work_saved(actors, client):
    _, master, _, worker, _, group = actors
    client.force_login(master)
    response = client.post(reverse("internal_time:new"), posted(group, worker, ends_at="06:00"), HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert "HX-Redirect" not in response.headers
    assert TeamReport.objects.count() == 0
    client.post(reverse("internal_time:new"), posted(group, worker, work_description="Доставка материала"))
    assert WorkType.objects.filter(name="Доставка материала").exists()


def test_anonymous_and_worker_denied(actors, client):
    assert client.get(reverse("internal_time:new")).status_code == 302
    regular = get_user_model().objects.create_user(username="ordinary")
    client.force_login(regular)
    assert client.get(reverse("internal_time:new")).status_code == 403


def test_minimal_project_permission(actors, client):
    from features.projects.group_services import create_project_group

    admin, master, _, _, _, _ = actors
    with pytest.raises(PermissionDenied):
        create_project_group(actor=master, name="Новый")
    group = create_project_group(actor=admin, name="Новый")
    assert group.responsible == admin
    assert group.edit_level == "admin"
    assert group.has_ac and group.has_dc


def test_cabinet_login_for_non_staff_master(actors, client):
    _, master, _, _, _, _ = actors
    password = uuid4().hex
    master.set_password(password)
    master.save()
    login_url = reverse("cabinet:account_login")
    target = reverse("internal_time:new")
    response = client.get(login_url, {"next": target})
    assert response.status_code == 200
    assert f'action="{login_url}"' in response.content.decode()
    response = client.post(login_url, {"username": master.username, "password": password, "next": target})
    assert response.status_code == 302
    assert response.url == target
    assert client.get(target).status_code == 200


def test_navigation_respects_direction_and_admin_permissions(actors, client):
    _, master, _, _, _, _ = actors
    client.force_login(master)
    response = client.get(reverse("internal_time:list"))
    html = response.content.decode()
    assert "/cabinet/ac/dashboard/" in html
    assert "/cabinet/dc/dashboard/" not in html
    assert "/cabinet/administration/dashboard/" not in html
    assert client.get("/ru/cabinet/dc/dashboard/").status_code == 403
    assert client.get("/ru/cabinet/administration/dashboard/").status_code == 403
    assert client.get("/ru/cabinet/ac/dashboard/").status_code == 200
    assert client.get(reverse("staff_employees")).status_code == 200


def test_team_owner_cannot_be_spoofed(actors):
    _, master, second, worker, other, _ = actors
    team = save_team(actor=master, name="Своя команда", owner=worker, members=[worker])
    with pytest.raises(PermissionDenied):
        save_team(actor=second, name="Чужая команда", owner=worker, members=[other], team_id=team.pk)
    team.refresh_from_db()
    assert team.name == "Своя команда"
    assert list(team.memberships.values_list("employee_id", flat=True)) == [worker.pk]


def test_partial_editor_does_not_validate_unfinished_fields(actors, client):
    admin, master, _, worker, _, group = actors
    client.force_login(master)
    response = client.post(
        reverse("internal_time:new"),
        posted(group, worker, action="add", project_group=""),
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert not response.context["form"].is_bound
    assert not response.context["formset"].is_bound
    response = client.post(reverse("internal_time:new"), posted(group, worker, action="team", team="invalid"))
    assert response.status_code == 200
    assert "Выберите доступную команду." in response.content.decode()
    client.force_login(admin)
    response = client.post(
        reverse("internal_time:new"),
        posted(group, worker, action="project", project_group="", new_project_name="Новый объект"),
    )
    assert response.status_code == 200
    created = ProjectGroup.objects.get(name="Новый объект")
    assert response.context["form"].initial["project_group"] == str(created.pk)
    assert TeamReport.objects.count() == 0
