"""Pure owner-scoped reads and prepared report data."""

from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from features.reporting.calculations import WorkCalculationSpec, calculate_position
from features.reporting.time import duration_minutes

from .models import DemoDailyReport, DemoWorkspace, DemoWorkType


def workspace_for_actor(actor):
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied
    return get_object_or_404(DemoWorkspace, owner=actor)


def work_types_for_actor(actor):
    return DemoWorkType.objects.filter(workspace=workspace_for_actor(actor))


def reports_for_actor(actor):
    return DemoDailyReport.objects.filter(workspace=workspace_for_actor(actor)).prefetch_related("workforce")


def report_for_actor(actor, pk):
    return get_object_or_404(
        reports_for_actor(actor).prefetch_related("entries__work_type", "entries__participants"), pk=pk
    )


def report_context(actor, pk):
    report = report_for_actor(actor, pk)
    entries = list(report.entries.all())
    totals = {"duration_hours": Decimal(0), "person_hours": Decimal(0)}
    for entry in entries:
        participants = list(entry.participants.all())
        result = calculate_position(
            work_type=WorkCalculationSpec(
                calculation_rule="actual", price_mode="zero", is_break=entry.work_type.is_break
            ),
            starts_at=entry.starts_at,
            ends_at=entry.ends_at,
            participant_count=len(participants),
            quantity=entry.quantity,
        )
        entry.calc_duration_hours = Decimal(duration_minutes(entry.starts_at, entry.ends_at)) / Decimal(60)
        entry.calc_person_hours = result.actual_person_hours
        entry.participant_names = ", ".join(person.name for person in participants)
        totals["duration_hours"] += entry.calc_duration_hours if not entry.work_type.is_break else Decimal(0)
        totals["person_hours"] += result.actual_person_hours
    return {"workspace": report.workspace, "report": report, "entries": entries, "totals": totals}


def export_snapshot(actor, pk):
    context = report_context(actor, pk)
    report = context["report"]
    day = {
        "date": report.date.isoformat(),
        "site_name": report.site_name,
        "project_number": report.project_number,
        "address": report.address,
        "group_name": "DEMO",
        "entries": [
            {
                "start": entry.starts_at.isoformat(),
                "end": entry.ends_at.isoformat(),
                "actual_person_hours": str(entry.calc_person_hours),
                "description": entry.work_type.name_de + (" - " + entry.description if entry.description else ""),
                "participants": [{"name": person.name} for person in entry.participants.all()],
            }
            for entry in context["entries"]
        ],
    }
    return {
        "document_title": "DEMO - Stundennachweis",
        "period_label": "Datum",
        "period_value": report.date.strftime("%d.%m.%Y"),
        "total_label": "Summe DEMO",
        "company_header": {
            "company_name": "DEMO - Musterfirma",
            "contact": "Fiktive Beispieldaten",
            "phone": "",
            "email": "",
        },
        "grouped": {report.pk: [day]},
    }
