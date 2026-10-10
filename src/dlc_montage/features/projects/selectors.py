"""Чтение проектов в пределах направления пользователя."""

from django.db.models import Q

from features.internal_time.policies import can_report, directions_for, is_manager

from .models import AcObject, ProjectGroup


def active_ac_groups():
    """Вернуть действующие Anlagen, в которых предусмотрены работы AC."""
    return ProjectGroup.objects.filter(has_ac=True, status="active").order_by("name", "pk")


def active_ac_objects_for_group(group_id):
    """Вернуть действующие AC-Standorte одной Anlage."""
    if not group_id or not str(group_id).isdigit():
        return AcObject.objects.none()
    return AcObject.objects.filter(
        group_id=group_id,
        is_active=True,
        group__has_ac=True,
        group__status="active",
    ).order_by("name", "pk")


def visible_groups(user, direction=None):
    groups = ProjectGroup.objects.select_related("client", "responsible", "deputy", "ac_responsible", "dc_responsible")
    if not can_report(user):
        return groups.none()
    if direction:
        if direction not in dict(directions_for(user)):
            return groups.none()
        groups = groups.filter(**{f"has_{direction}": True})
    if not is_manager(user):
        allowed = Q(pk__in=[])
        for key in dict(directions_for(user)):
            allowed |= Q(**{f"has_{key}": True})
        groups = groups.filter(allowed).exclude(status="deleted")
    return groups


def searchable_groups(user, *, query="", direction=None, limit=10):
    """Return a small permission-filtered list for remote comboboxes."""
    groups = visible_groups(user, direction).exclude(status__in=("deleted", "archived"))
    if query := query.strip():
        groups = groups.filter(
            Q(name__icontains=query)
            | Q(address__icontains=query)
            | Q(additional_addresses__icontains=query)
            | Q(client__name__icontains=query)
        )
    return groups.order_by("name", "pk")[:limit]


def searchable_ac_objects(user, *, group_id, query="", limit=10):
    """Return Standorte only from the selected visible AC Anlage."""
    if not group_id or not str(group_id).isdigit():
        return AcObject.objects.none()
    groups = visible_groups(user, "ac").filter(pk=group_id)
    objects = AcObject.objects.filter(group__in=groups, is_active=True)
    if query := query.strip():
        objects = objects.filter(
            Q(name__icontains=query) | Q(address__icontains=query) | Q(project_number__icontains=query)
        )
    return objects.order_by("name", "pk")[:limit]


def ac_dashboard_metrics(user):
    """Подготовить безопасные агрегированные счётчики и ссылки для рабочего стола AC."""
    from features.mbg_reports.models import MbgDailyReport
    from features.project_media.models import ProjectFile

    ac_groups = visible_groups(user, "ac").exclude(status="deleted")
    total_groups = ac_groups.count()
    active_groups = ac_groups.filter(status="active").count()

    ac_sites = AcObject.objects.filter(group__in=ac_groups, is_active=True)
    total_sites = ac_sites.count()
    started_sites = ac_sites.filter(status="started").count()
    completed_sites = ac_sites.filter(status="completed").count()

    ac_reports = MbgDailyReport.objects.filter(site__group__in=ac_groups)
    total_reports = ac_reports.count()
    accepted_reports = ac_reports.filter(status="accepted").count()
    pending_reports = ac_reports.filter(status="submitted").count()

    total_files = ProjectFile.objects.filter(group__in=ac_groups).count()
    recent_groups = tuple(ac_groups.order_by("-created_at", "-pk")[:6])

    return {
        "total_groups": total_groups,
        "active_groups": active_groups,
        "total_sites": total_sites,
        "started_sites": started_sites,
        "completed_sites": completed_sites,
        "total_reports": total_reports,
        "accepted_reports": accepted_reports,
        "pending_reports": pending_reports,
        "total_files": total_files,
        "recent_groups": recent_groups,
    }


def filtered_ac_groups(user, *, search="", status="active"):
    """Фильтрация групп AC (без DC-only) для оперативного списка CRM."""
    queryset = visible_groups(user, "ac").exclude(status="deleted").select_related("client")
    if search := search.strip():
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(address__icontains=search)
            | Q(client__name__icontains=search)
        )
    if status == "completed":
        queryset = queryset.filter(status="completed")
    elif status == "all":
        pass
    else:  # default active
        queryset = queryset.filter(status="active")
    return queryset.order_by("name", "pk")


def filtered_ac_objects(
    user,
    *,
    search="",
    group_id=None,
    status="non_completed",
    sort="activity",
):
    """Фильтрация и сортировка объектов AC до пагинации (исключая DC-only)."""
    from django.db.models import F, Max

    ac_groups = visible_groups(user, "ac").exclude(status="deleted")
    queryset = AcObject.objects.filter(group__in=ac_groups, is_active=True).select_related("group", "group__client")

    if group_id:
        scoped_group = ac_groups.filter(pk=group_id).first()
        if scoped_group is None:
            return queryset.none()
        queryset = queryset.filter(group=scoped_group)

    if search := search.strip():
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(address__icontains=search)
            | Q(project_number__icontains=search)
            | Q(group__name__icontains=search)
        )

    if status == "completed":
        queryset = queryset.filter(status="completed")
    elif status == "not_started":
        queryset = queryset.filter(status="not_started")
    elif status == "started":
        queryset = queryset.filter(status="started")
    elif status == "all":
        pass
    else:  # non_completed default
        queryset = queryset.filter(status__in=["not_started", "started"])

    if sort == "name":
        queryset = queryset.order_by("name", "pk")
    else:  # activity default
        queryset = queryset.annotate(
            latest_report_date=Max("mbg_reports__work_date")
        ).order_by(F("latest_report_date").desc(nulls_last=True), "-pk")

    return queryset

