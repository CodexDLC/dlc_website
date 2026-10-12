"""Atomic, owner-scoped persistence using the shared reporting rules."""

from datetime import time
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from features.reporting.validation import EntryInput, ReportValidationError, validate_report_entries

from .models import DemoDailyReport, DemoEmployee, DemoWorkEntry, DemoWorkspace, DemoWorkType

ERROR_MESSAGES = {
    "entries_count": "Bitte mindestens eine Tätigkeit hinzufügen.",
    "time_grid": "Zeiten müssen im 15-Minuten-Raster liegen; das Ende muss nach dem Beginn liegen.",
    "workforce": "Bitte Mitarbeiter auswählen.",
    "participants": "Bitte Mitarbeiter für jede Tätigkeit auswählen.",
    "participants_outside_workforce": "Teilnehmer müssen zur ausgewählten Mannschaft gehören.",
    "quantity": "Die Menge muss positiv sein.",
    "overlap": "Arbeitszeiten eines Mitarbeiters dürfen sich nicht überschneiden.",
}


def _authorized(actor):
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied


def _check_related(values, model, workspace):
    items = list(values)
    ids = [getattr(value, "pk", value) for value in items]
    if len(ids) != len(set(ids)) or model.objects.filter(workspace=workspace, pk__in=ids).count() != len(ids):
        raise ValidationError("Auswahl gehört nicht zu Ihrem Demo-Bereich.")
    return list(model.objects.filter(workspace=workspace, pk__in=ids))


def _seed(workspace):
    employees = [
        DemoEmployee.objects.create(workspace=workspace, name=name)
        for name in ("Anna Beispiel", "Lukas Muster", "Milan Demo")
    ]
    types = [
        DemoWorkType.objects.create(workspace=workspace, name_de=name, is_break=pause)
        for name, pause in (
            ("Montage Wechselrichter", False),
            ("Kabelverlegung", False),
            ("Anschluss UV-PV", False),
            ("Pause", True),
        )
    ]
    save_report(
        workspace.owner,
        data={
            "date": timezone.localdate(),
            "site_name": "DEMO - Musteranlage",
            "address": "Beispielstraße 10, 10115 Berlin",
            "project_number": "DEMO-001",
            "workforce": employees,
        },
        entries=[
            {
                "work_type": types[0],
                "participants": employees[:2],
                "starts_at": time(7),
                "ends_at": time(8),
                "quantity": 1,
                "description": "Beispiel: Montage und Befestigung",
            },
            {
                "work_type": types[3],
                "participants": employees[:2],
                "starts_at": time(8),
                "ends_at": time(8, 15),
                "quantity": 1,
            },
            {
                "work_type": types[1],
                "participants": employees[:2],
                "starts_at": time(8, 15),
                "ends_at": time(9),
                "quantity": 1,
            },
        ],
    )


@transaction.atomic
def ensure_workspace(actor):
    _authorized(actor)
    workspace, created = DemoWorkspace.objects.get_or_create(owner=actor)
    if created:
        _seed(workspace)
    return workspace


@transaction.atomic
def reset_workspace(actor):
    _authorized(actor)
    workspace = DemoWorkspace.objects.select_for_update().get(owner=actor)
    workspace.reports.all().delete()
    workspace.work_types.all().delete()
    workspace.employees.all().delete()
    _seed(workspace)


@transaction.atomic
def save_work_type(actor, *, data, work_type_id=None):
    _authorized(actor)
    workspace = DemoWorkspace.objects.select_for_update().get(owner=actor)
    if work_type_id:
        item = DemoWorkType.objects.select_for_update().filter(workspace=workspace, pk=work_type_id).first()
        if item is None:
            raise PermissionDenied
    else:
        item = DemoWorkType(workspace=workspace)
    for key in ("name_de", "unit", "is_break", "is_active"):
        if key in data:
            setattr(item, key, data[key])
    item.full_clean()
    item.save()
    return item


@transaction.atomic
def save_report(actor, *, data, entries, report_id=None):
    _authorized(actor)
    workspace = DemoWorkspace.objects.select_for_update().get(owner=actor)
    if report_id:
        report = DemoDailyReport.objects.select_for_update().filter(workspace=workspace, pk=report_id).first()
        if report is None:
            raise PermissionDenied
        if data.get("version") != report.version:
            raise ValidationError("Der Bericht wurde inzwischen geändert. Bitte neu laden und erneut bearbeiten.")
    else:
        report = DemoDailyReport(workspace=workspace)
    workforce = _check_related(data.get("workforce", []), DemoEmployee, workspace)
    prepared = []
    for entry in entries:
        work_type = _check_related([entry["work_type"]], DemoWorkType, workspace)[0]
        if not work_type.is_active:
            raise ValidationError("Bitte eine aktive Tätigkeit auswählen oder die Tätigkeit wieder aktivieren.")
        participants = _check_related(entry.get("participants", []), DemoEmployee, workspace)
        prepared.append({**entry, "work_type": work_type, "participants": participants})
    try:
        validate_report_entries(
            [
                EntryInput(
                    starts_at=entry["starts_at"],
                    ends_at=entry["ends_at"],
                    participant_ids=frozenset(person.pk for person in entry["participants"]),
                    quantity=Decimal(entry.get("quantity", 1)),
                )
                for entry in prepared
            ],
            workforce_ids=tuple(person.pk for person in workforce),
        )
    except ReportValidationError as exc:
        raise ValidationError(ERROR_MESSAGES.get(exc.code, "Ungültiger Bericht.")) from exc
    for key in ("date", "site_name", "address", "project_number"):
        if key in data:
            setattr(report, key, data[key])
    if report.pk:
        report.version += 1
    report.full_clean()
    report.save()
    report.workforce.set(workforce)
    report.entries.all().delete()
    for position, entry in enumerate(prepared):
        item = DemoWorkEntry.objects.create(
            report=report,
            work_type=entry["work_type"],
            starts_at=entry["starts_at"],
            ends_at=entry["ends_at"],
            quantity=entry.get("quantity", 1),
            description=entry.get("description", ""),
            position=position,
        )
        item.full_clean()
        item.participants.set(entry["participants"])
    return report
