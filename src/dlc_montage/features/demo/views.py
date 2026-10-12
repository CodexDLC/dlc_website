"""German-only demo HTTP delivery; services own every mutation."""

from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.views.decorators.http import require_POST

from features.mbg_reports.export_workbooks import build_weekly_workbook

from . import selectors, services
from .forms import EntryForm, EntryFormSet, ReportForm, WorkTypeForm


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
        initial={"date": timezone.localdate()} if not report else None,
    )
    formset = EntryFormSet(
        request.POST or None, initial=initial_entries, prefix="entries", form_kwargs={"workspace": workspace}
    )
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "add" or action.startswith(("remove:", "move:")):
            rows = _editor_rows(request.POST)
            if action == "add" and len(rows) < 100:
                rows.append(_new_entry(rows, request.POST.getlist("workforce")))
            elif action.startswith("remove:"):
                try:
                    index = int(action.split(":")[1])
                    if 0 <= index < len(rows):
                        rows.pop(index)
                except ValueError:
                    pass
            elif action.startswith("move:"):
                try:
                    _, raw_index, direction = action.split(":", maxsplit=2)
                    index = int(raw_index)
                    target = index - 1 if direction == "up" else index + 1
                    if direction in {"up", "down"} and 0 <= index < len(rows) and 0 <= target < len(rows):
                        rows[index], rows[target] = rows[target], rows[index]
                except ValueError:
                    pass
            initial = {key: request.POST.get(key, "") for key in ReportForm.base_fields}
            initial["workforce"] = request.POST.getlist("workforce")
            form = ReportForm(instance=report, workspace=workspace, initial=initial)
            formset = EntryFormSet(initial=rows, prefix="entries", form_kwargs={"workspace": workspace})
        else:
            valid = form.is_valid()
            valid = formset.is_valid() and valid
            if valid:
                entries = [row for row in formset.cleaned_data if row]
                try:
                    report = services.save_report(request.user, data=form.cleaned_data, entries=entries, report_id=pk)
                except ValidationError as exc:
                    form.add_error(None, exc)
                else:
                    url = reverse("demo:report_detail", kwargs={"pk": report.pk})
                    return (
                        HttpResponse(headers={"HX-Redirect": url})
                        if request.headers.get("HX-Request")
                        else redirect(url)
                    )
    elif not report:
        formset = EntryFormSet(initial=[_new_entry([], [])], prefix="entries", form_kwargs={"workspace": workspace})
    template = "_report_editor" if request.headers.get("HX-Request") else "report_form"
    return _render(
        request,
        template,
        {"workspace": workspace, "form": form, "formset": formset, "report": report, "demo_editor": True},
    )


def _editor_rows(post):
    """Keep unfinished posted cards intact for the AC editor's structural actions."""
    try:
        count = min(max(int(post.get("entries-TOTAL_FORMS", "0")), 0), 100)
    except ValueError:
        count = 0
    rows = []
    for index in range(count):
        row = {key: post.get(f"entries-{index}-{key}", "") for key in EntryForm.base_fields}
        row["participants"] = post.getlist(f"entries-{index}-participants")
        rows.append(row)
    return rows


def _new_entry(rows, workforce):
    """Start the next discrete quarter-hour card at the previous card's end."""
    try:
        start = time.fromisoformat(rows[-1].get("ends_at", "")) if rows else time(7)
    except ValueError:
        start = time(7)
    end = (datetime.combine(timezone.localdate(), start) + timedelta(minutes=15)).time()
    if end <= start:
        start, end = time(7), time(7, 15)
    return {"starts_at": start, "ends_at": end, "participants": workforce, "quantity": 1}


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
