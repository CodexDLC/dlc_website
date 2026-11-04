"""Запись явных соответствий между планом объекта и расчётным каталогом."""

from decimal import ROUND_CEILING, Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from features.customer_portal.audit import record_event
from features.internal_time.policies import is_manager
from features.projects.models import AcObject, SiteWorkItem
from features.work_catalog.models import CustomerWorkPosition

from .models import CustomerWorkPackage, CustomerWorkRequirement
from .policies import can_export_reports


def package_snapshot(package):
    """Сохранить состав и правило начисления для аудита изменений."""
    return {
        "site_id": package.site_id,
        "position_id": package.position_id,
        "label": package.label,
        "quantity": str(package.quantity) if package.quantity is not None else None,
        "manual_confirmed": package.manual_confirmed,
        "note": package.note,
        "is_active": package.is_active,
        "requirements": list(package.requirements.values("work_item_id", "required_quantity")),
    }


@transaction.atomic
def save_customer_package(
    *, actor, site, position, label, quantity, items=(), manual_confirmed=False, note="", is_active=True, pk=None
):
    """Привязать конкретные работы без изменения принятых отчётов или времени."""
    if not can_export_reports(actor):
        raise PermissionDenied
    return _save_customer_package(
        actor=actor,
        site=site,
        position=position,
        label=label,
        quantity=quantity,
        items=items,
        manual_confirmed=manual_confirmed,
        note=note,
        is_active=is_active,
        pk=pk,
    )


def _save_customer_package(
    *, actor, site, position, label, quantity, items=(), manual_confirmed=False, note="", is_active=True, pk=None
):
    """Общий проверенный путь записи для явных и автоматических назначений."""
    site = AcObject.objects.select_for_update().select_related("group").get(pk=site.pk)
    if not site.is_active or not site.group.has_ac:
        raise ValidationError("Ein aktiver AC-Standort ist erforderlich.")
    position = CustomerWorkPosition.objects.get(pk=position.pk)
    if not position.is_active and (not pk or is_active):
        raise ValidationError("Die Kundenposition ist nicht aktiv.")
    try:
        quantity = Decimal(str(quantity)) if quantity not in (None, "") else None
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError("Ungültige Abrechnungsmenge.") from exc
    if quantity is not None and (not quantity.is_finite() or quantity <= 0):
        raise ValidationError("Die Abrechnungsmenge muss positiv sein.")
    ids = [item.pk for item in items]
    if len(ids) != len(set(ids)):
        raise ValidationError("Eine physische Position darf nicht doppelt ausgewählt werden.")
    items = list(SiteWorkItem.objects.filter(pk__in=ids).select_related("work_type", "route", "cable_type"))
    if len(items) != len(ids) or any(item.site_id != site.pk or (is_active and not item.is_required) for item in items):
        raise ValidationError("Alle Arbeiten müssen zum Standort gehören und erforderlich sein.")
    if is_active and position.manual_only and not manual_confirmed:
        raise ValidationError("Diese Position benötigt vorerst eine manuell bestätigte Menge mit Begründung.")
    if manual_confirmed and (quantity is None or not note.strip()):
        raise ValidationError("Manuelle Bestätigung benötigt Menge und Begründung.")
    if not items and not note.strip():
        raise ValidationError("Ohne zugeordnete Arbeiten ist eine Begründung erforderlich.")
    codes = {item.work_type.code for item in items}
    required_codes = {
        "10.010": {"uv-montage", "uv-anschluss"},
        "01.0180": {"cable-laying", "hpas-anschluss"},
    }
    if is_active and items and position.code in required_codes and codes != required_codes[position.code]:
        raise ValidationError("Das Paket benötigt sowohl Montage/Verlegung als auch den zugehörigen Anschluss.")
    if is_active and items and position.code == "10.010":
        if len(items) != 2 or len({item.planned_quantity for item in items}) != 1:
            raise ValidationError("Montage und Anschluss müssen dieselbe Anzahl physischer Geräte betreffen.")
        if quantity is not None and quantity != items[0].planned_quantity:
            raise ValidationError("Die Paketmenge entspricht der Anzahl physischer Geräte, nicht der Anschlüsse.")
    if is_active and items and position.code == "01.0060":
        legacy_pair = len(items) == 2 and codes == {"nh-montage", "nh-anschluss"}
        single_nh = len(items) == 1 and codes <= {"nh-montage", "nh-anschluss"}
        extension = (
            len(items) == 1
            and codes == {"cable-laying"}
            and items[0].route
            and items[0].route.code == "nh-existing-cable-extension"
        )
        if not (legacy_pair or single_nh or extension):
            raise ValidationError(
                "NH-Position benötigt eine Montage, einen Anschluss oder die Verlängerung der Bestandsleitung."
            )
        if legacy_pair and (
            len({item.planned_quantity for item in items}) != 1 or quantity not in (None, items[0].planned_quantity)
        ):
            raise ValidationError("Montage und Anschluss müssen dieselbe Anzahl physischer Geräte betreffen.")
        if single_nh and quantity not in (None, items[0].planned_quantity):
            raise ValidationError("Die Menge entspricht der Anzahl physischer NH-Geräte.")
        if extension and quantity not in (None, Decimal("1")):
            raise ValidationError("Für die Verlängerung wird eine Einheit angesetzt.")
    if (
        is_active
        and items
        and position.code == "01.0180"
        and any(
            item.work_type.code == "cable-laying"
            and (
                not item.route
                or item.route.code != "uv-hpas-new"
                or not item.cable_type
                or item.cable_type.category != "potential"
            )
            for item in items
        )
    ):
        raise ValidationError("Für UV-PV-HPAS ist die eigene PE-Leitung dieses Weges erforderlich.")
    route_codes = {"01.0140": {"wr-uv"}, "01.0150": {"uv-nh-new", "uv-hv"}, "01.0160": {"nh-new-hv"}}
    if is_active and items and position.code in route_codes:
        if not any(item.work_type.code == "cable-laying" for item in items) or any(
            item.work_type.code not in {"cable-laying", "cable-tray"}
            or not item.route
            or item.route.code not in route_codes[position.code]
            or (item.work_type.code == "cable-laying" and item.cable_type.category not in {"power", "heavy"})
            for item in items
        ):
            raise ValidationError(
                "Der Weg enthält Leistungskabel und gegebenenfalls Trasse; Patchkabel bleiben separat."
            )
    if position.code == "01.0180" and quantity not in (None, Decimal("1")):
        raise ValidationError("UV-PV-HPAS wird einmal je Standort abgerechnet.")
    if (
        position.code == "01.0180"
        and CustomerWorkPackage.objects.filter(site=site, position=position, is_active=True).exclude(pk=pk).exists()
        and is_active
    ):
        raise ValidationError("UV-PV-HPAS ist für diesen Standort bereits zugeordnet.")
    # A tray can serve several inverter paths; construction is an additional service on a mounting item.
    duplicate_items = [item.pk for item in items if item.work_type.code != "cable-tray"]
    duplicates = (
        CustomerWorkRequirement.objects.filter(work_item_id__in=duplicate_items, package__is_active=True)
        .exclude(package_id=pk)
        .exclude(package__position__code="01.0050")
    )
    if is_active and position.code != "01.0050" and duplicates.exists():
        raise ValidationError("Eine ausgewählte Arbeit gehört bereits zu einem anderen Abrechnungspaket.")
    if (
        is_active
        and position.code == "01.0050"
        and CustomerWorkRequirement.objects.filter(
            work_item_id__in=ids, package__position=position, package__is_active=True
        )
        .exclude(package_id=pk)
        .exists()
    ):
        raise ValidationError("Die Unterkonstruktion ist bereits einem Paket zugeordnet.")
    package = (
        CustomerWorkPackage.objects.select_for_update().get(pk=pk, site=site) if pk else CustomerWorkPackage(site=site)
    )
    before = package_snapshot(package) if package.pk else {}
    package.position, package.label = position, label.strip()
    package.quantity, package.manual_confirmed = quantity, manual_confirmed
    package.note, package.is_active = note.strip(), is_active
    package.full_clean()
    package.save()
    previous = {r.work_item_id: r.required_quantity for r in package.requirements.all()}
    package.requirements.all().delete()
    CustomerWorkRequirement.objects.bulk_create(
        [
            CustomerWorkRequirement(
                package=package, work_item=item, required_quantity=previous.get(item.pk, item.planned_quantity)
            )
            for item in items
        ]
    )
    after = package_snapshot(package)
    # Audit JSON must not contain Decimal objects.
    for snapshot in (before, after):
        for requirement in snapshot.get("requirements", []):
            requirement["required_quantity"] = str(requirement["required_quantity"])
    record_event(
        actor=actor, action="customer_package_saved", target=package, before=before, after=after, reason=package.note
    )
    return package


@transaction.atomic
def prepare_customer_packages(*, actor, site):
    """Подготовить только однозначные пакеты; повторный запуск ничего не дублирует."""
    if not is_manager(actor):
        raise PermissionDenied
    site = AcObject.objects.select_for_update().get(pk=site.pk)
    items = list(
        SiteWorkItem.objects.filter(site=site, is_required=True).select_related("work_type", "route", "cable_type")
    )
    positions = {p.code: p for p in CustomerWorkPosition.objects.filter(is_active=True, manual_only=False)}
    used = set(CustomerWorkRequirement.objects.filter(package__site=site).values_list("work_item_id", flat=True))
    created = []

    def add(code, label, components, quantity=1):
        if not components or code not in positions:
            return
        if CustomerWorkPackage.objects.filter(site=site, position=positions[code], label=label).exists():
            return
        if code != "01.0050" and any(i.pk in used for i in components if i.work_type.code != "cable-tray"):
            return
        created.append(
            _save_customer_package(
                actor=actor,
                site=site,
                position=positions[code],
                label=label,
                quantity=quantity,
                items=components,
                note="Zuordnung aus dem eindeutigen Standortplan.",
            )
        )
        if code != "01.0050":
            used.update(i.pk for i in components if i.work_type.code != "cable-tray")

    def by_code(code):
        return [i for i in items if i.work_type.code == code]

    for mount_code, connect_code, price_code, name in (("uv-montage", "uv-anschluss", "10.010", "UV-PV"),):
        mounts, connections = by_code(mount_code), by_code(connect_code)
        if len(mounts) == len(connections) == 1 and mounts[0].planned_quantity == connections[0].planned_quantity:
            add(price_code, name, mounts + connections, mounts[0].planned_quantity)
    for work in (i for i in items if i.work_type.code in {"nh-montage", "nh-anschluss"}):
        add("01.0060", f"{work.work_type.code}: {work.label} ({work.pk})", [work], work.planned_quantity)
    for work in (i for i in by_code("cable-laying") if i.route and i.route.code == "nh-existing-cable-extension"):
        add("01.0060", f"Zusätzliches Kabel zur Verlängerung der Bestandsleitung ({work.pk})", [work])
    for work_code, price_code in (("wr-montage", "01.0020"), ("wr-anschluss", "10.020"), ("erder", "01.0070")):
        for work in by_code(work_code):
            add(price_code, work.label, [work], work.planned_quantity)
    for work in items:
        if work.with_underconstruction and work.work_type.code in {"wr-montage", "uv-montage", "nh-montage"}:
            add("01.0050", f"Unterkonstruktion: {work.label}", [work], work.planned_quantity)
    pe = [i for i in by_code("cable-laying") if i.route and i.route.code == "uv-hpas-new"]
    hpas = by_code("hpas-anschluss")
    if len(pe) == len(hpas) == 1:
        add("01.0180", "UV-PV-HPAS", pe + hpas)
    for work in by_code("cable-laying"):
        if work.route and work.route.code == "uv-key-switch" and work.cable_type.code == "control-7x1-5":
            add("01.0040", work.label, [work])
    for route_code, price_code in (
        ("wr-uv", "01.0140"),
        ("uv-nh-new", "01.0150"),
        ("uv-hv", "01.0150"),
        ("nh-new-hv", "01.0160"),
    ):
        cables = [
            i
            for i in by_code("cable-laying")
            if i.route and i.route.code == route_code and i.cable_type.category in {"power", "heavy"}
        ]
        trays = [i for i in by_code("cable-tray") if i.route and i.route.code == route_code]
        # Several physical runs can share a direction; do not guess the route/equipment identity.
        if len(cables) == 1 and len(trays) <= 1:
            work = cables[0]
            units = work.planned_quantity / (2 if work.cable_type.category == "heavy" else 1)
            quantity = units.to_integral_value(rounding=ROUND_CEILING)
            add(price_code, str(work.route), cables + trays, quantity)
    return tuple(created)
