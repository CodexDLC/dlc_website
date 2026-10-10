from decimal import Decimal
from django.db import migrations


def forward_migrate_material(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    MbgWorkEntry = apps.get_model("mbg_reports", "MbgWorkEntry")
    MbgReportRevision = apps.get_model("mbg_reports", "MbgReportRevision")

    try:
        delivery_type = WorkType.objects.get(code="material-delivery")
    except WorkType.DoesNotExist:
        return

    # Update MbgWorkEntry
    entries = MbgWorkEntry.objects.filter(work_type__code="material")
    for entry in entries:
        entry.work_type = delivery_type
        entry.unit_price = Decimal("50.00")
        qty = entry.quantity or Decimal("1.00")
        entry.amount = (qty * Decimal("50.00")).quantize(Decimal("0.01"))
        entry.save(update_fields=["work_type", "unit_price", "amount"])

    # Update MbgReportRevision snapshots
    for rev in MbgReportRevision.objects.all():
        snapshot = rev.snapshot
        if not snapshot or "entries" not in snapshot:
            continue
        changed = False
        for e in snapshot["entries"]:
            if e.get("work_type_code") == "material":
                e["work_type_code"] = "material-delivery"
                e["unit"] = "psch."
                e["calculation_rule"] = "fixed"
                e["unit_price"] = "50.00"
                try:
                    qty = Decimal(str(e.get("quantity", "1")))
                except Exception:
                    qty = Decimal("1")
                e["amount"] = str((qty * Decimal("50.00")).quantize(Decimal("0.01")))
                changed = True
        if changed:
            rev.snapshot = snapshot
            rev.save(update_fields=["snapshot"])


def reverse_migrate_material(apps, schema_editor):
    WorkType = apps.get_model("work_catalog", "WorkType")
    MbgWorkEntry = apps.get_model("mbg_reports", "MbgWorkEntry")
    MbgReportRevision = apps.get_model("mbg_reports", "MbgReportRevision")

    try:
        old_material = WorkType.objects.get(code="material")
    except WorkType.DoesNotExist:
        return

    entries = MbgWorkEntry.objects.filter(work_type__code="material-delivery")
    for entry in entries:
        entry.work_type = old_material
        entry.unit_price = Decimal("40.00")
        entry.amount = (Decimal(str(entry.actual_person_hours or 0)) * Decimal("40.00")).quantize(Decimal("0.01"))
        entry.save(update_fields=["work_type", "unit_price", "amount"])

    for rev in MbgReportRevision.objects.all():
        snapshot = rev.snapshot
        if not snapshot or "entries" not in snapshot:
            continue
        changed = False
        for e in snapshot["entries"]:
            if e.get("work_type_code") == "material-delivery":
                e["work_type_code"] = "material"
                e["unit"] = "Std."
                e["calculation_rule"] = "actual"
                e["unit_price"] = "40.00"
                hours = Decimal(str(e.get("actual_person_hours", "0")))
                e["amount"] = str((hours * Decimal("40.00")).quantize(Decimal("0.01")))
                changed = True
        if changed:
            rev.snapshot = snapshot
            rev.save(update_fields=["snapshot"])


class Migration(migrations.Migration):
    dependencies = [
        ("mbg_reports", "0010_mbgworkentry_work_item"),
        ("work_catalog", "0013_separate_material_delivery_and_unloading"),
    ]

    operations = [
        migrations.RunPython(forward_migrate_material, reverse_migrate_material),
    ]
