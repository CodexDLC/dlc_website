"""German-only demo HTTP delivery; services own every mutation."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone, translation
from django.views.decorators.http import require_POST

from features.mbg_reports.export_workbooks import build_weekly_workbook

from . import selectors, services
from .forms import EntryFormSet, ReportForm, WorkTypeForm


def _prepare(request):
    request.cabinet_module = "demo"
    translation.activate("de")
    request.LANGUAGE_CODE = "de"
    return services.ensure_workspace(request.user)


def _render(request, template, context):
    with translation.override("de"):
        return render(request, "demo/" + template + ".html", context)


@login_required
def home(request):
    return redirect("demo:work_types")


@login_required
def work_types(request):
    workspace = _prepare(request)
    return _render(
        request, "work_types", {"workspace": workspace, "work_types": selectors.work_types_for_actor(request.user)}
    )


@login_required
def work_type_edit(request, pk=None):
    workspace = _prepare(request)
    item = get_object_or_404(selectors.work_types_for_actor(request.user), pk=pk) if pk else None
    form = WorkTypeForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        services.save_work_type(request.user, data=form.cleaned_data, work_type_id=pk)
        return redirect("demo:work_types")
    return _render(request, "work_type_form", {"workspace": workspace, "form": form, "work_type": item})


@login_required
def reports(request):
    workspace = _prepare(request)
    return _render(request, "reports", {"workspace": workspace, "reports": selectors.reports_for_actor(request.user)})


@login_required
def report_edit(request, pk=None):
    workspace = _prepare(request)
    report = selectors.report_for_actor(request.user, pk) if pk else None
    initial_entries = (
        [
            {
                "work_type": entry.work_type_id,
                "participants": [person.pk for person in entry.participants.all()],
                "starts_at": entry.starts_at,
                "ends_at": entry.ends_at,
                "quantity": entry.quantity,
                "description": entry.description,
            }
            for entry in report.entries.all()
        ]
        if report
        else []
    )
    form = ReportForm(
        request.POST or None,
        instance=report,
        workspace=workspace,
        initial={"date": timezone.localdate(), "workforce": list(workspace.employees.all())} if not report else None,
    )
    formset = EntryFormSet(
        request.POST or None, initial=initial_entries, prefix="entries", form_kwargs={"workspace": workspace}
    )
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        entries = [row for row in formset.cleaned_data if row and not row.get("DELETE")]
        try:
            report = services.save_report(request.user, data=form.cleaned_data, entries=entries, report_id=pk)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            return redirect("demo:report_detail", pk=report.pk)
    return _render(request, "report_form", {"workspace": workspace, "form": form, "formset": formset, "report": report})


@login_required
def report_detail(request, pk):
    _prepare(request)
    return _render(request, "report_detail", selectors.report_context(request.user, pk))


@login_required
def report_download(request, pk):
    _prepare(request)
    payload = build_weekly_workbook(selectors.export_snapshot(request.user, pk))
    response = HttpResponse(payload, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="DEMO-Stundennachweis-{pk}.xlsx"'
    return response


@login_required
@require_POST
def reset(request):
    _prepare(request)
    services.reset_workspace(request.user)
    return redirect("demo:reports")
