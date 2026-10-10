from django.db import migrations, models


def backfill_custom_descriptions(apps, schema_editor):
    """Отделить известный сгенерированный хвост от пользовательского текста."""
    entry_model = apps.get_model("mbg_reports", "MbgWorkEntry")
    entries = entry_model.objects.using(schema_editor.connection.alias).select_related(
        "work_type", "route", "cable_type"
    )
    for entry in entries.iterator():
        description = entry.description
        work_name = entry.work_type.name_de if entry.work_type else ""
        details = []
        if entry.route_id:
            details.append(entry.route.name_de)
        if entry.cable_type_id:
            details.append(entry.cable_type.name_de)
        if entry.with_underconstruction:
            details.append("mit Unterkonstruktion")
        if entry.standard_connections:
            details.append(f"{entry.standard_connections} Standardanschlüsse")
        if entry.heavy_connections:
            details.append(f"{entry.heavy_connections} Schweranschlüsse")
        if entry.quantity != 1:
            details.append(f"× {format(entry.quantity.normalize(), 'f')}")  # noqa: RUF001

        suffix = f" · {' · '.join(details)}" if details else ""
        if description == f"{work_name}{suffix}":
            custom = ""
        elif suffix and description.endswith(suffix) and len(description) > len(suffix):
            custom = description[: -len(suffix)]
        else:
            custom = description
        entry_model.objects.using(schema_editor.connection.alias).filter(pk=entry.pk).update(custom_description=custom)


class Migration(migrations.Migration):
    dependencies = [("mbg_reports", "0008_performanceexport_document_type")]

    operations = [
        migrations.AddField(
            model_name="mbgworkentry",
            name="custom_description",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.RunPython(backfill_custom_descriptions, migrations.RunPython.noop),
    ]
