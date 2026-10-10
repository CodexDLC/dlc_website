"""Чтение отчётов и данных для интерфейса."""

from django.db.models import Q

from features.crews.models import Crew
from features.projects.models import ProjectGroup
from features.staff.models import Employee

from .calculations import duration_minutes, format_minutes
from .models import TeamReport, WorkType
from .policies import directions_for, employee_for, is_manager


def visible_reports(user):
    reports = TeamReport.objects.select_related("project_group", "author").prefetch_related("participants__employee")
    if not is_manager(user):
        reports = reports.filter(author=user, direction__in=dict(directions_for(user)))
    return reports


def available_groups(user, query=""):
    direction_keys = dict(directions_for(user))
    allowed = Q(pk__in=[])
    if "ac" in direction_keys:
        allowed |= Q(has_ac=True)
    if "dc" in direction_keys:
        allowed |= Q(has_dc=True)
    return ProjectGroup.objects.filter(allowed, status="active", name__icontains=query)


def available_employees():
    return Employee.objects.filter(employment_status=Employee.EmploymentStatus.ACTIVE)


def available_teams(user):
    teams = Crew.objects.filter(is_active=True).prefetch_related("memberships__employee")
    return teams if is_manager(user) else teams.filter(owner=employee_for(user))


def work_types():
    return WorkType.objects.all()


def report_summary(report):
    base = duration_minutes(report.starts_at, report.ends_at)
    members = [
        {
            "employee": member.employee,
            "deduction": member.deduction_minutes,
            "hours": format_minutes(base - member.deduction_minutes),
        }
        for member in report.participants.all()
    ]
    return {
        "members": members,
        "base": format_minutes(base),
        "total": format_minutes(sum(base - m["deduction"] for m in members)),
    }


def filtered_reports(user, filters):
    reports = visible_reports(user)
    for field in ("direction", "status", "project_group", "author", "participants__employee"):
        value = filters.get(field)
        if value:
            if field in ("project_group", "author", "participants__employee") and not value.isdigit():
                continue
            reports = reports.filter(**{field: value})
    from django.utils.dateparse import parse_date

    for name, lookup in (("from", "work_date__gte"), ("to", "work_date__lte")):
        try:
            value = parse_date(filters.get(name, ""))
        except ValueError:
            value = None
        if value:
            reports = reports.filter(**{lookup: value})
    return reports.distinct()
