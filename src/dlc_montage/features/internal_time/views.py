"""HTTP-адаптеры редактора, списка и проверки внутренних отчётов."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from features.projects.group_services import create_project_group

from . import selectors
from .forms import ParticipantFormSet, QuickProjectForm, ReportForm
from .models import TeamReport
from .policies import can_create_group, can_edit, can_report, is_manager
from .services import review_report, save_report


def prepare_request(request):
    """Установить пространство кабинета и проверить доступ к самой функции."""
    if not can_report(request.user):
        raise PermissionDenied
    request.cabinet_space = "staff"
    request.cabinet_module = "staff"


@login_required
def report_list(request):
    prepare_request(request)
    reports = selectors.filtered_reports(request.user, request.GET)
    page = Paginator(reports, 30).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "internal_time/list.html",
        {
            "page": page,
            "query": query.urlencode(),
            "filters": request.GET,
            "rows": [{"report": report, **selectors.report_summary(report)} for report in page],
            "groups": selectors.available_groups(request.user),
            "employees": selectors.available_employees(),
            "statuses": TeamReport.Status.choices,
            "manager": is_manager(request.user),
            "authors": reports.values("author_id", "author__username").distinct(),
        },
    )


def render_editor(request, form, formset, report=None, errors=()):
    """Возвратить общий редактор отдельно либо внутри оболочки CRM."""
    template = "internal_time/_editor.html" if request.headers.get("HX-Request") else "internal_time/editor.html"
    return render(
        request,
        template,
        {
            "form": form,
            "formset": formset,
            "report": report,
            "errors": errors,
            "teams": selectors.available_teams(request.user),
            "work_types": selectors.work_types(),
            "can_create_group": can_create_group(request.user),
            "manager": is_manager(request.user),
            "post_url": request.path,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def report_editor(request, pk=None):
    prepare_request(request)
    report = get_object_or_404(selectors.visible_reports(request.user), pk=pk) if pk else None
    if report and not can_edit(request.user, report):
        return redirect("internal_time:detail", pk=report.pk)
    existing_ids = [m.employee_id for m in report.participants.all()] if report else []
    initial = (
        {field: getattr(report, field) for field in ReportForm.base_fields if hasattr(report, field)} if report else {}
    )
    members = (
        [{"employee": m.employee_id, "deduction_minutes": m.deduction_minutes} for m in report.participants.all()]
        if report
        else []
    )
    if request.method == "GET":
        return render_editor(
            request,
            ReportForm(user=request.user, report=report, initial=initial),
            ParticipantFormSet(initial=members, prefix="members", form_kwargs={"employee_ids": existing_ids}),
            report,
        )
    data = request.POST.copy()
    action = data.get("action", "draft")
    errors = []
    # Операции редактора изменяют только отправленную форму; команда — шаблон состава.
    if action in ("add", "team") or action.startswith("remove:"):
        try:
            count = min(max(int(data.get("members-TOTAL_FORMS", 0)), 0), 100)
        except ValueError:
            count = 0
        rows = [
            {
                "employee": data.get(f"members-{i}-employee", ""),
                "deduction_minutes": data.get(f"members-{i}-deduction_minutes", "0"),
            }
            for i in range(count)
        ]
        if action == "add":
            rows.append({"employee": "", "deduction_minutes": "0"})
        elif action == "team":
            team_key = data.get("team", "")
            team = selectors.available_teams(request.user).filter(pk=team_key if team_key.isdigit() else None).first()
            if team:
                present = {str(row["employee"]) for row in rows}
                rows = [row for row in rows if row["employee"]]
                rows.extend(
                    {"employee": str(m.employee_id), "deduction_minutes": "0"}
                    for m in team.memberships.all()
                    if str(m.employee_id) not in present and m.employee.employment_status == "active"
                )
            else:
                errors.append(_("Выберите доступную команду."))
        else:
            try:
                rows.pop(int(action.split(":")[1]))
            except (ValueError, IndexError):
                errors.append(_("Строка уже удалена."))
        for i, row in enumerate(rows[:100]):
            for key, value in row.items():
                data[f"members-{i}-{key}"] = value
        data["members-TOTAL_FORMS"] = str(min(len(rows), 100))
        data["members-INITIAL_FORMS"] = "0"
    if action == "project":
        project_form = QuickProjectForm({"name": data.get("new_project_name")})
        if project_form.is_valid():
            try:
                group = create_project_group(actor=request.user, **project_form.cleaned_data)
                data["project_group"] = str(group.pk)
            except ValidationError as exc:
                errors.extend(exc.messages)
        else:
            errors.append(_("Укажите название нового проекта."))
    if action not in ("draft", "submit"):
        initial = {key: data.get(key) for key in ReportForm.base_fields}
        try:
            count = min(max(int(data.get("members-TOTAL_FORMS", 0)), 0), 100)
        except ValueError:
            count = 0
        member_initial = [
            {
                "employee": data.get(f"members-{i}-employee", ""),
                "deduction_minutes": data.get(f"members-{i}-deduction_minutes", "0"),
            }
            for i in range(count)
        ]
        return render_editor(
            request,
            ReportForm(initial=initial, user=request.user, report=report),
            ParticipantFormSet(initial=member_initial, prefix="members", form_kwargs={"employee_ids": existing_ids}),
            report,
            errors,
        )
    form = ReportForm(data, user=request.user, report=report)
    formset = ParticipantFormSet(data, prefix="members", form_kwargs={"employee_ids": existing_ids})
    if action in ("draft", "submit"):
        valid = form.is_valid()
        valid = formset.is_valid() and valid
        if valid:
            try:
                saved = save_report(
                    actor=request.user,
                    data=form.cleaned_data,
                    participants=[row.cleaned_data for row in formset if row.cleaned_data],
                    submit=action == "submit",
                    report_id=pk,
                    version=form.cleaned_data.get("version"),
                    reason=form.cleaned_data["reason"],
                )
                url = reverse("internal_time:detail", kwargs={"pk": saved.pk})
                if request.headers.get("HX-Request"):
                    return HttpResponse(headers={"HX-Redirect": url})
                return redirect(url)
            except ValidationError as exc:
                errors.extend(exc.messages)
    return render_editor(request, form, formset, report, errors)


@login_required
def report_detail(request, pk):
    prepare_request(request)
    report = get_object_or_404(selectors.visible_reports(request.user), pk=pk)
    return render(
        request,
        "internal_time/detail.html",
        {
            "report": report,
            **selectors.report_summary(report),
            "editable": can_edit(request.user, report),
            "manager": is_manager(request.user),
            "revisions": report.revisions.select_related("actor")[:30],
        },
    )


@login_required
@require_POST
def report_review(request, pk):
    prepare_request(request)
    get_object_or_404(selectors.visible_reports(request.user), pk=pk)
    try:
        version = int(request.POST.get("version", "0"))
        review_report(
            actor=request.user,
            report_id=pk,
            decision=request.POST.get("decision"),
            version=version,
            reason=request.POST.get("reason", ""),
        )
    except (ValueError, ValidationError) as exc:
        message = _("Некорректная версия отчёта.") if isinstance(exc, ValueError) else " ".join(exc.messages)
        from django.contrib import messages

        messages.error(request, message)
    return redirect("internal_time:detail", pk=pk)
