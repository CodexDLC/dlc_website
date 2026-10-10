"""Браузерный ввод и выдача клиентских документов."""

from datetime import time, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from features.internal_time.policies import is_manager
from features.projects.models import AcObject, ProjectGroup, SiteWorkItem
from features.projects.selectors import active_ac_objects_for_group

from .exports import (
    generate_final_hours,
    generate_performance_report,
    generate_site_performance_report,
    generate_week,
    generate_work_completion_report,
)
from .forms import EntryFormSet, ReportForm, ReportListFilterForm, WeekForm
from .models import FinalHourlyExport, PerformanceExport, WeeklyExport
from .policies import can_export_reports
from .selectors import (
    completed_group_position_summary,
    employee_day_schedule,
    export_hub_context,
    filtered_reports_for,
    group_position_summary,
    priced_performance_exports_for_group,
    reports_for,
    site_position_summary_map,
    site_work_history,
)
from .services import review_report, save_report


def prepare(request):
    if not is_manager(request.user):
        raise PermissionDenied
    request.cabinet_module = "ac"


def prepare_export(request):
    if not can_export_reports(request.user):
        raise PermissionDenied
    request.cabinet_module = "ac"


def new_report_initial(request):
    """Прочитать безопасные значения для предварительного заполнения формы."""
    initial = {}
    for field in ("group", "site"):
        value = request.GET.get(field, "")
        if value.isdigit():
            initial[field] = int(value)
    work_date = parse_date(request.GET.get("work_date", ""))
    if work_date:
        initial["work_date"] = work_date
    workforce = [int(value) for value in request.GET.getlist("workforce") if value.isdigit()]
    if workforce:
        initial["workforce"] = workforce
    return initial


def new_report_url(*, group_id, work_date, workforce_ids, site_id=None):
    """Собрать ссылку на ту же форму с заполненной шапкой."""
    params = [("group", group_id), ("work_date", work_date.isoformat())]
    if site_id:
        params.append(("site", site_id))
    params.extend(("workforce", employee_id) for employee_id in workforce_ids)
    return f"{reverse('mbg_reports:new')}?{urlencode(params)}"


@login_required
def report_list(request):
    prepare(request)
    form = ReportListFilterForm(request.GET or None)
    filters = form.cleaned_data if form.is_valid() else {}
    qs = filtered_reports_for(request.user, filters)
    reports = list(qs[:100])

    from collections import defaultdict

    days_dict = defaultdict(list)
    for r in reports:
        days_dict[r.work_date].append(r)
    report_days = [{"date": d, "reports": days_dict[d]} for d in sorted(days_dict.keys(), reverse=True)]

    return render(
        request,
        "mbg_reports/list.html",
        {
            "reports": reports,
            "report_days": report_days,
            "filter_form": form,
            "can_export": can_export_reports(request.user),
        },
    )


@login_required
def export_hub(request):
    """Единый экран документов AC/MBG: сгруппированные объекты, акты, табели и ведомость."""
    prepare(request)
    request.cabinet_module = "ac"

    can_manage = can_export_reports(request.user)

    q_all = request.GET.get("q", "").strip()[:100]
    q_group = request.GET.get("q_group", "").strip()[:100]
    q_pdf = request.GET.get("q_pdf", "").strip()[:100]
    if q_all and not q_group and not q_pdf:
        q_group = q_all
        q_pdf = q_all

    page_groups = request.GET.get("page_groups", 1)
    page_pdf = request.GET.get("page_pdf", 1)
    page_weeks = request.GET.get("page_weeks", 1)
    page_completion = request.GET.get("page_completion", 1)

    from features.customer_portal.selectors import customer_documents_context

    context = customer_documents_context(
        request.user,
        search_group=q_group,
        search_pdf=q_pdf,
        page_groups=page_groups,
        page_pdf=page_pdf,
        per_page=20,
    )

    for group in context["groups_page"]:
        for site in group.ac_objects.all():
            site.settlement_report_url = reverse("mbg_reports:site_performance_export", kwargs={"site_id": site.pk})
            site.payment_toggle_url = reverse("mbg_reports:site_payment_toggle", kwargs={"site_id": site.pk})

    hub_ctx = export_hub_context(
        q_group or q_all,
        page_weeks=page_weeks,
        page_completion=page_completion,
    )
    context.update(hub_ctx)

    if q_all:
        weeks_pagination_params = urlencode({"q": q_all, "page_completion": 1})
        completion_pagination_params = urlencode({"q": q_all, "page_weeks": 1})
    else:
        weeks_pagination_params = urlencode(
            {
                "q_group": q_group,
                "q_pdf": q_pdf,
                "page_groups": str(page_groups),
                "page_pdf": str(page_pdf),
            }
        )
        completion_pagination_params = ""

    context.update(
        {
            "can_manage_settlement": can_manage,
            "batch_settlement_report_url": reverse("mbg_reports:batch_settlement_report"),
            "download_common_excel_url": reverse("mbg_reports:master_excel_download"),
            "update_google_sheets_url": reverse("mbg_reports:google_sheets_sync"),
            "q": q_all,
            "query": q_all,
            "q_group": q_group,
            "q_pdf": q_pdf,
            "page_groups": page_groups,
            "page_pdf": page_pdf,
            "weeks_pagination_params": weeks_pagination_params,
            "completion_pagination_params": completion_pagination_params,
        }
    )

    return render(
        request,
        "mbg_reports/unified_documents.html",
        context,
    )


@login_required
@require_POST
def batch_settlement_report(request):
    """Сформировать отчёт для выставления счёта по выбранным Standorte (только администратор)."""
    prepare_export(request)
    from django.contrib import messages

    site_ids = [int(x) for x in request.POST.getlist("site_ids") if x.isdigit()]
    include_paid = request.POST.get("include_paid") in ("1", "true", "True")

    if not site_ids:
        messages.error(request, _("Выберите хотя бы один объект для формирования счёта."))
        return redirect("mbg_reports:export_hub")

    sites = list(AcObject.objects.filter(pk__in=site_ids).select_related("group"))
    if len(sites) != len(site_ids):
        messages.error(request, _("Некоторые из выбранных объектов не найдены."))
        return redirect("mbg_reports:export_hub")

    if any(not s.group.has_ac for s in sites):
        messages.error(request, _("Все выбранные объекты должны относиться к направлению AC."))
        return redirect("mbg_reports:export_hub")

    if not include_paid and any(s.is_paid for s in sites):
        messages.error(request, _("Оплаченные объекты исключены из нового счёта."))
        return redirect("mbg_reports:export_hub")

    try:
        artifact = generate_performance_report(
            actor=request.user,
            site_ids=[s.pk for s in sites],
            include_paid=include_paid,
        )
        return redirect("mbg_reports:performance_download", pk=artifact.pk)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("mbg_reports:export_hub")


@login_required
def master_excel_download(request):
    """Скачать общую сводную ведомость по проектам и объектам (Excel) без сетевых запросов."""
    prepare_export(request)
    from features.mbg_reports.master_workbook import build_master_settlement_bytes

    data = build_master_settlement_bytes()
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="DLC_Montage_AC_Gesamtabrechnung.xlsx"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def google_sheets_sync(request):
    """Явное обновление Google Таблицы по POST-запросу администратора с CSRF."""
    prepare_export(request)
    from django.contrib import messages
    from loguru import logger

    from features.mbg_reports.google_sync import sync_master_to_google_sheets

    try:
        result = sync_master_to_google_sheets()
        messages.success(
            request,
            _("Лист Übersicht Google Таблицы успешно обновлён ({count} объектов).").format(
                count=result.get("synced_sites_count", 0)
            ),
        )
    except Exception as exc:
        logger.error("Google Sheets sync failed: {}", exc)
        messages.error(request, _("Ошибка синхронизации с Google Таблицей: {error}").format(error=str(exc)))

    return redirect("mbg_reports:export_hub")


@login_required
@require_POST
def site_payment_toggle(request, site_id):
    """Изменение статуса оплаты отдельного Standort администратором."""
    prepare_export(request)
    from django.contrib import messages

    from features.projects.settlement import set_site_payment_status

    site = get_object_or_404(AcObject.objects.select_related("group"), pk=site_id)
    if not site.group.has_ac:
        messages.error(request, _("Объект не относится к направлению AC."))
        return redirect("mbg_reports:export_hub")

    raw_is_paid = request.POST.get("is_paid")
    target_is_paid = raw_is_paid in ("1", "true", "True") if raw_is_paid is not None else not site.is_paid
    note = request.POST.get("note", "").strip()
    reason = request.POST.get("reason", "").strip()

    try:
        set_site_payment_status(
            actor=request.user,
            site_id=site.pk,
            is_paid=target_is_paid,
            note=note,
            reason=reason,
        )
        status_label = _("Оплачено") if target_is_paid else _("К оплате")
        messages.success(
            request,
            _("Статус оплаты Standort '{name}' изменён: {status}.").format(
                name=site.name,
                status=status_label,
            ),
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))

    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect("mbg_reports:export_hub")


@login_required
def multi_performance_export(request):
    """Сформировать общий Zwischennachweis или Leistungsnachweis по нескольким/всем проектам."""
    prepare_export(request)
    from django.contrib import messages

    if request.method == "POST":
        mode = request.POST.get("mode", "preliminary")
        is_preliminary = mode == "preliminary"
        scope = request.POST.get("scope", "all")
        site_ids = [int(x) for x in request.POST.getlist("site_ids") if x.isdigit()]
        group_ids = [int(x) for x in request.POST.getlist("group_ids") if x.isdigit()]

        try:
            if scope == "custom" and not site_ids and not group_ids:
                raise ValidationError(_("Выберите хотя бы один объект для формирования акта."))

            artifact = generate_performance_report(
                actor=request.user,
                group_ids=group_ids or None,
                site_ids=site_ids or None,
                is_preliminary=is_preliminary,
            )
            return redirect("mbg_reports:performance_download", pk=artifact.pk)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

    return redirect("mbg_reports:export_hub")


@login_required
@require_POST
def work_completion_export(request):
    """Выпустить нефинансовый Leistungsnachweis по Anlage либо одному Standort."""
    prepare_export(request)
    from django.contrib import messages

    scope = request.POST.get("scope")
    raw_id = request.POST.get("scope_id", "")
    if scope not in {"group", "site"} or not raw_id.isdigit():
        messages.error(request, _("Выберите проект или объект для отчёта о выполненных работах."))
        return redirect("mbg_reports:export_hub")
    try:
        artifact = generate_work_completion_report(
            actor=request.user,
            group_id=int(raw_id) if scope == "group" else None,
            site_id=int(raw_id) if scope == "site" else None,
        )
        return redirect("mbg_reports:performance_download", pk=artifact.pk)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("mbg_reports:export_hub")


@login_required
def editor(request, pk=None):
    prepare(request)
    report = get_object_or_404(reports_for(request.user), pk=pk) if pk else None
    require_reason = bool(report and report.status == "accepted")
    initial = (
        {
            "group": report.site.group_id,
            "site": report.site_id,
            "work_date": report.work_date,
            "workforce": list(report.workforce.values_list("pk", flat=True)),
            "version": report.version,
            "submission_key": report.submission_key,
        }
        if report
        else new_report_initial(request)
    )
    rows = (
        [
            {
                "participants": list(entry.participants.values_list("pk", flat=True)),
                "starts_at": entry.starts_at,
                "ends_at": entry.ends_at,
                "work_type": entry.work_type_id,
                "work_item": entry.work_item_id,
                "completed_quantity": entry.completed_quantity,
                "quantity": entry.quantity,
                "cable_type": entry.cable_type_id,
                "route": entry.route_id,
                "standard_connections": entry.standard_connections,
                "heavy_connections": entry.heavy_connections,
                "with_underconstruction": entry.with_underconstruction,
                "internal_only": entry.internal_only,
                "description": entry.custom_description,
            }
            for entry in report.entries.prefetch_related("participants")
        ]
        if report
        else []
    )
    form = ReportForm(initial=initial, require_reason=require_reason)
    formset = EntryFormSet(initial=rows, prefix="entries", form_kwargs={"site_id": form["site"].value()})
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "add" or action.startswith(("remove:", "move:")):
            try:
                count = min(max(int(request.POST.get("entries-TOTAL_FORMS", "0")), 0), 100)
            except ValueError:
                count = 0
            keys = (
                "starts_at",
                "ends_at",
                "work_type",
                "work_item",
                "completed_quantity",
                "quantity",
                "cable_type",
                "route",
                "standard_connections",
                "heavy_connections",
                "with_underconstruction",
                "internal_only",
                "description",
            )
            rows = []
            for i in range(count):
                row = {key: request.POST.get(f"entries-{i}-{key}", "") for key in keys}
                row["participants"] = request.POST.getlist(f"entries-{i}-participants")
                rows.append(row)
            if action == "add":
                rows.append({})
            elif action.startswith("remove:"):
                try:
                    index = int(action.split(":")[1])
                    if index >= 0:
                        rows.pop(index)
                except (ValueError, IndexError):
                    pass
            elif action.startswith("move:"):
                try:
                    _, raw_index, direction = action.split(":", maxsplit=2)
                    index = int(raw_index)
                    target_index = index - 1 if direction == "up" else index + 1
                    if direction in {"up", "down"} and 0 <= index < len(rows) and 0 <= target_index < len(rows):
                        rows[index], rows[target_index] = rows[target_index], rows[index]
                except ValueError:
                    pass
            report_initial = {key: request.POST.get(key) for key in ReportForm.base_fields}
            report_initial["workforce"] = request.POST.getlist("workforce")
            form = ReportForm(initial=report_initial, require_reason=require_reason)
            formset = EntryFormSet(initial=rows[:100], prefix="entries", form_kwargs={"site_id": form["site"].value()})
        else:
            form = ReportForm(request.POST, require_reason=require_reason)
            formset = EntryFormSet(request.POST, prefix="entries", form_kwargs={"site_id": form["site"].value()})
            valid = form.is_valid()
            valid = formset.is_valid() and valid
            if valid:
                try:
                    saved = save_report(
                        actor=request.user,
                        report_id=pk,
                        entries=[f.cleaned_data for f in formset if f.cleaned_data],
                        submit=action == "submit",
                        **{key: value for key, value in form.cleaned_data.items() if key != "group"},
                    )
                    url = reverse("mbg_reports:detail", args=[saved.pk])
                    return (
                        HttpResponse(headers={"HX-Redirect": url})
                        if request.headers.get("HX-Request")
                        else redirect(url)
                    )
                except ValidationError as exc:
                    form.add_error(None, exc)
    selected_site = form["site"].value()
    selected_site_id = int(selected_site) if str(selected_site or "").isdigit() else None
    history = (
        site_work_history(site_id=selected_site_id, exclude_report_id=report.pk if report else None)
        if selected_site_id
        else None
    )
    template = "mbg_reports/_editor.html" if request.headers.get("HX-Request") else "mbg_reports/editor.html"
    return render(
        request,
        template,
        {"form": form, "formset": formset, "report": report, "site_history": history},
    )


@login_required
def site_options(request):
    """Обновить список Standort после выбора Anlage."""
    prepare(request)
    group_id = request.GET.get("group", "")
    sites = active_ac_objects_for_group(group_id)
    form = ReportForm(initial={"group": group_id})
    return render(
        request,
        "mbg_reports/_site_field.html",
        {
            "site": form["site"],
            "group_selected": bool(group_id and group_id.isdigit()),
            "has_sites": sites.exists(),
        },
    )


@login_required
def site_history(request):
    """Обновить справочную историю работ после выбора Standort."""
    prepare(request)
    site_id = request.GET.get("site", "")
    exclude_report = request.GET.get("exclude_report", "")
    history = (
        site_work_history(
            site_id=int(site_id),
            exclude_report_id=int(exclude_report) if exclude_report.isdigit() else None,
        )
        if site_id.isdigit()
        else None
    )
    return render(request, "mbg_reports/_site_history.html", {"site_history": history})


@login_required
def work_item_options(request):
    """Передать только позиции выбранного AC-Standort для дневного редактора."""
    prepare(request)
    site_id = request.GET.get("site", "")
    if not site_id.isdigit():
        return JsonResponse({"items": []})
    items = SiteWorkItem.objects.filter(
        site_id=site_id, site__is_active=True, site__group__has_ac=True, site__group__status="active"
    ).order_by("pk")
    return JsonResponse(
        {
            "items": [
                {
                    "id": item.pk,
                    "label": item.label,
                    "work_type": item.work_type_id,
                    "route": item.route_id,
                    "cable_type": item.cable_type_id,
                    "with_underconstruction": item.with_underconstruction,
                }
                for item in items
            ]
        }
    )


@login_required
def employee_availability(request):
    """Выдать занятые интервалы MBG для оперативной проверки формы."""
    prepare(request)
    work_date = parse_date(request.GET.get("work_date", ""))
    employee_ids = [value for value in request.GET.getlist("employee") if value.isdigit()]
    exclude_report = request.GET.get("exclude_report", "")
    if not work_date or not employee_ids:
        return JsonResponse({"employees": []})
    return JsonResponse(
        {
            "employees": employee_day_schedule(
                work_date=work_date,
                employee_ids=employee_ids,
                exclude_report_id=int(exclude_report) if exclude_report.isdigit() else None,
            )
        }
    )


@login_required
def detail(request, pk):
    prepare(request)
    report = get_object_or_404(reports_for(request.user), pk=pk)
    snapshot = report.revisions.get(version=report.version).snapshot
    workforce_ids = [
        str(item.get("employee_id") or item.get("id"))
        for item in snapshot.get("workforce", [])
        if item.get("employee_id") or item.get("id")
    ] or [str(w.id) for w in report.workforce.all()]

    def calc_entry_minutes(e):
        if "minutes" in e and e["minutes"] is not None:
            return int(e["minutes"]) * len(e.get("participants", []))
        if e.get("actual_person_hours") is not None:
            return int(Decimal(str(e["actual_person_hours"])) * Decimal(60))
        if e.get("start") and e.get("end"):
            st = e["start"]
            en = e["end"]
            st_t = st if isinstance(st, time) else time.fromisoformat(str(st))
            en_t = en if isinstance(en, time) else time.fromisoformat(str(en))
            return ((en_t.hour * 60 + en_t.minute) - (st_t.hour * 60 + st_t.minute)) * len(e.get("participants", []))
        return 0

    return render(
        request,
        "mbg_reports/detail.html",
        {
            "report": report,
            "snapshot": snapshot,
            "total_minutes": sum(calc_entry_minutes(e) for e in snapshot.get("entries", [])),
            "revisions": report.revisions.select_related("actor"),
            "can_export": can_export_reports(request.user),
            "next_day_url": new_report_url(
                group_id=report.site.group_id,
                site_id=report.site_id,
                work_date=report.work_date + timedelta(days=1),
                workforce_ids=workforce_ids,
            ),
            "other_site_url": new_report_url(
                group_id=report.site.group_id,
                work_date=report.work_date,
                workforce_ids=workforce_ids,
            ),
        },
    )


@login_required
@require_POST
def review(request, pk):
    prepare(request)
    get_object_or_404(reports_for(request.user), pk=pk)
    from django.contrib import messages

    try:
        review_report(
            actor=request.user,
            report_id=pk,
            version=int(request.POST.get("version", "0")),
            decision=request.POST.get("decision"),
            reason=request.POST.get("reason", ""),
        )
    except (ValidationError, ValueError) as exc:
        messages.error(
            request, " ".join(exc.messages) if isinstance(exc, ValidationError) else _("Некорректная версия.")
        )
    return redirect("mbg_reports:detail", pk=pk)


@login_required
def exports(request):
    prepare_export(request)
    today = timezone.localdate().isocalendar()
    requested_year = request.GET.get("year", "")
    requested_week = request.GET.get("week", "")
    initial = {
        "year": int(requested_year) if requested_year.isdigit() else today.year,
        "week": int(requested_week) if requested_week.isdigit() else today.week,
    }
    form = WeekForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            artifact = generate_week(actor=request.user, **form.cleaned_data)
            return redirect("mbg_reports:download", pk=artifact.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "mbg_reports/exports.html",
        {
            "form": form,
            "exports": WeeklyExport.objects.order_by("-pk"),
            "can_export": True,
        },
    )


@login_required
def group_overview(request, group_id):
    """Показать выполненные и нулевые позиции по всей Anlage."""
    prepare_export(request)
    group = get_object_or_404(ProjectGroup, pk=group_id)
    return render(
        request,
        "mbg_reports/group_overview.html",
        {"group": group, "rows": group_position_summary(group), "can_export": True},
    )


@login_required
def performance_exports(request, group_id):
    """Выпуск Leistungsnachweis (завершённых) и Zwischennachweis (выбранных) Standorte."""
    prepare_export(request)
    group = get_object_or_404(ProjectGroup, pk=group_id, has_ac=True)
    all_sites = list(group.ac_objects.filter(is_active=True).order_by("name", "pk"))
    completed_sites = [s for s in all_sites if s.status == "completed"]

    sites_data = []
    positions_by_site = site_position_summary_map([site.pk for site in all_sites])
    for site in all_sites:
        accepted_reports = site.mbg_reports.filter(status="accepted").count()
        total_reports = site.mbg_reports.count()
        summary = positions_by_site[site.pk]
        summary_rows = [row for row in summary.rows if row.sources]
        known_subtotal = sum((row.amount for row in summary_rows if row.amount is not None), Decimal("0"))
        total_amount = (
            None if summary.excluded_reports or any(row.amount is None for row in summary_rows) else known_subtotal
        )
        sites_data.append(
            {
                "site": site,
                "accepted_reports": accepted_reports,
                "total_reports": total_reports,
                "amount": total_amount,
                "known_subtotal": known_subtotal,
                "has_accepted": accepted_reports > 0,
            }
        )

    if request.method == "POST":
        from django.contrib import messages

        mode = request.POST.get("mode", "final")
        try:
            if mode == "preliminary":
                raw_ids = request.POST.getlist("site_ids")
                site_ids = [int(x) for x in raw_ids if x.isdigit()]
                if not site_ids:
                    raise ValidationError(_("Выберите хотя бы один Standort для промежуточного отчёта."))
                artifact = generate_performance_report(
                    actor=request.user,
                    group_id=group.pk,
                    site_ids=site_ids,
                    is_preliminary=True,
                )
            else:
                artifact = generate_performance_report(
                    actor=request.user,
                    group_id=group.pk,
                    is_preliminary=False,
                )
            return redirect("mbg_reports:performance_download", pk=artifact.pk)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

    return render(
        request,
        "mbg_reports/performance_exports.html",
        {
            "group": group,
            "sites_data": sites_data,
            "completed_sites": completed_sites,
            "rows": completed_group_position_summary(group),
            "exports": priced_performance_exports_for_group(group),
            "can_export": True,
        },
    )


@login_required
def site_performance_export(request, site_id):
    """Быстрая выгрузка Leistungsnachweis / Zwischennachweis для конкретного Standort."""
    prepare_export(request)
    site = get_object_or_404(AcObject.objects.select_related("group"), pk=site_id)
    from django.contrib import messages

    if not site.group.has_ac:
        messages.error(request, _("Объект не относится к направлению AC."))
        return redirect("mbg_reports:export_hub")

    include_paid = request.GET.get("include_paid") == "1" or request.POST.get("include_paid") == "1"
    try:
        is_preliminary = site.status != "completed"
        artifact = generate_site_performance_report(
            actor=request.user,
            site_id=site.pk,
            is_preliminary=is_preliminary,
            include_paid=include_paid,
        )
        return redirect("mbg_reports:performance_download", pk=artifact.pk)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("mbg_reports:export_hub")


@login_required
@require_POST
def final_hours_export(request, group_id):
    """Сформировать итоговый почасовой Stundennachweis завершённой Anlage."""
    prepare_export(request)
    from django.contrib import messages

    try:
        artifact = generate_final_hours(actor=request.user, group_id=group_id)
        return redirect("mbg_reports:final_hours_download", pk=artifact.pk)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("mbg_reports:export_hub")


@login_required
def download(request, pk):
    prepare_export(request)
    artifact = get_object_or_404(WeeklyExport, pk=pk)
    response = FileResponse(
        artifact.file.open("rb"),
        as_attachment=True,
        filename=artifact.filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def performance_download(request, pk):
    prepare_export(request)
    artifact = get_object_or_404(PerformanceExport, pk=pk)
    response = FileResponse(
        artifact.file.open("rb"),
        as_attachment=True,
        filename=artifact.filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def final_hours_download(request, pk):
    prepare_export(request)
    artifact = get_object_or_404(FinalHourlyExport, pk=pk)
    response = FileResponse(
        artifact.file.open("rb"),
        as_attachment=True,
        filename=artifact.filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Cache-Control"] = "private, no-store"
    return response
