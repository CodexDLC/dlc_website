import django.db.models.deletion
from django.db import migrations, models


def copy_performance_group(apps, schema_editor):
    PerformanceExport = apps.get_model("mbg_reports", "PerformanceExport")
    for export in PerformanceExport.objects.select_related("site").iterator():
        export.group_id = export.site.group_id
        export.save(update_fields=["group"])


class Migration(migrations.Migration):
    dependencies = [("mbg_reports", "0004_performanceexport")]

    operations = [
        migrations.RemoveField(model_name="weeklyexport", name="group"),
        migrations.AddField(
            model_name="performanceexport",
            name="group",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="performance_exports",
                to="projects.projectgroup",
            ),
        ),
        migrations.RunPython(copy_performance_group, migrations.RunPython.noop),
        migrations.RemoveField(model_name="performanceexport", name="site"),
        migrations.AlterField(
            model_name="performanceexport",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="performance_exports",
                to="projects.projectgroup",
            ),
        ),
    ]
