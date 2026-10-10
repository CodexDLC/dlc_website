"""Страницы проектов; запись выполняется через сервисы."""

from dataclasses import replace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from features.internal_time.policies import can_report, is_manager

from .forms import ClientForm, GroupForm, ObjectForm, SiteWorkItemForm, TypicalPlanForm
from .models import AcObject, Client, ProjectGroup, SiteWorkItem
from .policies import can_edit_group, can_use_files
from .read_models import (
    ac_group_cards,
    build_group_card,
    internal_daily_work,
    site_activity,
    site_work_plan,
    typical_plan_preview,
)
from .selectors import searchable_ac_objects, searchable_groups, visible_groups
from .services import (
    apply_typical_site_plan,
    save_group,
    save_object,
    save_site_work_item,
    set_site_status,
    set_work_item_lifecycle,
)
from .typical_plan import build_typical_plan


@login_required
def group_list(request, direction=None):
    if not can_report(request.user) or (direction is None and not is_manager(request.user)):
        raise PermissionDenied
    request.cabinet_module = direction or "administration"

    q = request.GET.get("q", "").strip()[:100]
    status = request.GET.get("status", "active").strip()
    if status not in {"active", "completed", "all"}:
        status = "active"

    if direction == "ac":
        from .selectors import filtered_ac_groups

        groups_qs = filtered_ac_groups(request.user, search=q, status=status)
    else:
        groups_qs = visible_groups(request.user, direction)
        if q:
            groups_qs = groups_qs.filter(name__icontains=q)
        if status == "completed":
            groups_qs = groups_qs.filter(status="completed")
        elif status == "active":
            groups_qs = groups_qs.filter(status="active")

    from django.core.paginator import Paginator

    page_obj = Paginator(groups_qs, 20).get_page(request.GET.get("page"))

    return render(
        request,
        "projects/list.html",
        {
            "groups": page_obj,
            "groups_page": page_obj,
            "query": q,
            "status": status,
            "direction": direction,
            "manager": is_manager(request.user),
        },
    )


@login_required
def group_detail(request, pk):
    group = get_object_or_404(visible_groups(request.user), pk=pk)
    request.cabinet_module = "ac" if group.has_ac else "dc"
    group_activity = build_group_card(group, group.ac_objects.all())
    return render(
        request,
        "projects/detail.html",
        {
            "group": group,
            "group_activity": group_activity,
            "site_cards": group_activity.sites,
            "editable": can_edit_group(request.user, group),
            "manager": is_manager(request.user),
            "export_allowed": request.user.is_superuser,
            "files_allowed": can_use_files(request.user, group),
        },
    )


@login_required
def group_edit(request, pk=None):
    request.cabinet_module = "administration" if is_manager(request.user) else "ac"
    group = get_object_or_404(visible_groups(request.user), pk=pk) if pk else None
    if not (is_manager(request.user) or (group and can_edit_group(request.user, group))):
        raise PermissionDenied
    form = GroupForm(request.POST or None, user=request.user, instance=group)
    if request.method == "POST" and form.is_valid():
        try:
            group = save_group(actor=request.user, group_id=pk, data=form.cleaned_data)
            return redirect("projects:detail", pk=group.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "projects/group_form.html",
        {
            "form": form,
            "title": _("Карточка проекта"),
            "back": reverse("projects:detail", args=[pk]) if pk else reverse("projects:list"),
        },
    )


@login_required
def object_edit(request, group_id, pk=None):
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "ac"
    group = get_object_or_404(ProjectGroup, pk=group_id)
    obj = get_object_or_404(AcObject, pk=pk, group=group) if pk else None
    form = ObjectForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            save_object(actor=request.user, group=group, data=form.cleaned_data, object_id=pk)
            return redirect("projects:detail", pk=group.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "cabinet/components/entity_form.html", {"form": form, "title": _("AC-объект")})


@login_required
def object_list(request):
    request.cabinet_module = "ac"
    if not can_report(request.user):
        raise PermissionDenied

    from django.core.paginator import Paginator

    from features.customer_portal.selectors import attach_site_plan_progress, get_cached_photo_summary

    from .selectors import filtered_ac_objects

    query = request.GET.get("q", "").strip()[:100]
    group_id = request.GET.get("group", "").strip()
    if not group_id.isdigit():
        group_id = ""

    status = request.GET.get("status", "non_completed").strip()
    if status not in {"non_completed", "completed", "all", "not_started", "started"}:
        status = "non_completed"

    sort = request.GET.get("sort", "activity").strip()
    if sort not in {"activity", "name"}:
        sort = "activity"

    sites_qs = filtered_ac_objects(
        request.user,
        search=query,
        group_id=group_id,
        status=status,
        sort=sort,
    )
    page_obj = Paginator(sites_qs, 20).get_page(request.GET.get("page"))

    for s in page_obj:
        s.cached_photo_summary = get_cached_photo_summary(s)
    attach_site_plan_progress(page_obj.object_list)

    ac_groups = visible_groups(request.user, "ac").exclude(status="deleted").order_by("name", "pk")
    selected_group = ac_groups.filter(pk=group_id).first() if group_id else None

    return render(
        request,
        "projects/objects.html",
        {
            "sites": page_obj,
            "sites_page": page_obj,
            "group_cards": ac_group_cards(request.user),
            "query": query,
            "group_id": group_id,
            "selected_group": selected_group,
            "status": status,
            "sort": sort,
            "groups": ac_groups,
            "manager": is_manager(request.user),
        },
    )


@login_required
def group_choices(request):
    """Search Anlagen for reusable server-backed comboboxes."""
    direction = request.GET.get("direction")
    if direction not in {"ac", "dc"}:
        direction = None
    groups = searchable_groups(
        request.user,
        query=request.GET.get("q", ""),
        direction=direction,
    )
    return JsonResponse(
        {
            "results": [
                {
                    "value": str(group.pk),
                    "label": group.name,
                    "meta": " · ".join(part for part in (group.address, str(group.client or "")) if part),
                }
                for group in groups
            ]
        }
    )


@login_required
def site_choices(request):
    """Search Standorte within one selected and visible Anlage."""
    sites = searchable_ac_objects(
        request.user,
        group_id=request.GET.get("group", ""),
        query=request.GET.get("q", ""),
    )
    return JsonResponse(
        {
            "results": [
                {
                    "value": str(site.pk),
                    "label": f"{site.name} · P/Nr {site.project_number or '—'}",
                    "meta": site.address,
                }
                for site in sites
            ]
        }
    )


@login_required
def site_detail(request, group_id, pk):
    """Read-first operational workspace for one AC Standort."""
    group = get_object_or_404(visible_groups(request.user, "ac"), pk=group_id)
    site = get_object_or_404(AcObject.objects.select_related("group"), pk=pk, group=group)
    request.cabinet_module = "ac"
    from features.customer_portal.selectors import accepted_completion_rows
    from features.integrations.nextcloud.services import get_site_photo_summary
    from features.mbg_reports.models import MbgDailyReport
    from features.mbg_reports.selectors import site_position_summary
    from features.project_media.models import ProjectFile

    reports = list(
        MbgDailyReport.objects.filter(site=site)
        .prefetch_related("workforce")
        .annotate(person_hours=Sum("entries__actual_person_hours"))
        .order_by("-work_date", "-pk")
    )
    positions = [row for row in site_position_summary(site) if row.quantity or row.actual_person_hours or row.amount]
    completed_rows = accepted_completion_rows(site)
    photo_summary = get_site_photo_summary(site)
    customer_files = list(ProjectFile.objects.filter(site=site, customer_visible=True, content_type="application/pdf"))
    daily_work = internal_daily_work(site)

    return render(
        request,
        "projects/object_detail.html",
        {
            "group": group,
            "site": site,
            "activity": site_activity(site),
            "reports": reports,
            "positions": positions,
            "work_plan": site_work_plan(site),
            "completed_rows": completed_rows,
            "photo_summary": photo_summary,
            "show_photos": request.GET.get("show_photos") == "1",
            "files": customer_files,
            "daily_work": daily_work,
            "manager": is_manager(request.user),
            "editable": is_manager(request.user),
            "export_allowed": request.user.is_superuser,
            "files_allowed": can_use_files(request.user, group),
        },
    )


@login_required
def work_item_edit(request, group_id, site_id, pk=None):
    """Редактировать отдельную физическую позицию Standort."""
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "ac"
    site = get_object_or_404(AcObject.objects.select_related("group"), pk=site_id, group_id=group_id)
    item = get_object_or_404(SiteWorkItem, pk=pk, site=site) if pk else None
    form = SiteWorkItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            save_site_work_item(
                actor=request.user,
                site=site,
                work_item_id=pk,
                **form.cleaned_data,
            )
            return redirect("projects:site_detail", group_id=group_id, pk=site_id)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "projects/work_item_form.html", {"form": form, "site": site, "item": item})


@login_required
def typical_work_plan(request, group_id, site_id):
    """Предпросмотр и однократное создание редактируемого AC-плана."""
    if not is_manager(request.user):
        raise PermissionDenied
    site = get_object_or_404(AcObject.objects.select_related("group"), pk=site_id, group_id=group_id)
    request.cabinet_module = "ac"
    if site.work_items.exists():
        return redirect("projects:site_detail", group_id=group_id, pk=site_id)
    form = TypicalPlanForm(request.POST or None)
    specs = ()
    preview_rows = ()
    if request.method == "POST" and form.is_valid():
        config = form.to_config()
        specs = build_typical_plan(config)
        try:
            preview_rows = typical_plan_preview(specs)
        except ValidationError as exc:
            form.add_error(None, exc)
        if request.POST.get("step") == "apply" and preview_rows:
            preview_rows = tuple(
                replace(
                    row,
                    selected=bool(request.POST.get(f"include-{row.spec.key}")),
                    quantity=request.POST.get(f"quantity-{row.spec.key}", str(row.spec.planned_quantity)),
                )
                for row in preview_rows
            )
            selected = {row.spec.key: row.quantity for row in preview_rows if row.selected}
            try:
                apply_typical_site_plan(actor=request.user, site=site, config=config, selected=selected)
                return redirect("projects:site_detail", group_id=group_id, pk=site_id)
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(
        request,
        "projects/typical_work_plan.html",
        {
            "site": site,
            "form": form,
            "preview_rows": preview_rows,
        },
    )


@login_required
@require_POST
def site_status(request, group_id, pk):
    """Быстрая смена статуса Standort менеджером."""
    if not is_manager(request.user):
        raise PermissionDenied
    group = get_object_or_404(ProjectGroup, pk=group_id)
    site = get_object_or_404(AcObject, pk=pk, group=group)
    try:
        set_site_status(actor=request.user, site=site, status=request.POST.get("status"))
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("projects:site_detail", group_id=group.pk, pk=site.pk)


@login_required
@require_POST
def work_item_lifecycle(request, group_id, site_id, pk):
    """Решение менеджера по одной физической позиции плана."""
    if not is_manager(request.user):
        raise PermissionDenied
    item = get_object_or_404(SiteWorkItem, pk=pk, site_id=site_id, site__group_id=group_id)
    try:
        set_work_item_lifecycle(
            actor=request.user, item=item, action=request.POST.get("action"), reason=request.POST.get("reason", "")
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    return redirect("projects:site_detail", group_id=group_id, pk=site_id)


@login_required
def clients(request, pk=None):
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "administration"
    obj = get_object_or_404(Client, pk=pk) if pk else None
    form = ClientForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        from .services import save_client

        save_client(actor=request.user, data=form.cleaned_data, client_id=pk)
        return redirect("projects:clients")
    return render(request, "projects/clients.html", {"form": form, "clients": Client.objects.all()})
