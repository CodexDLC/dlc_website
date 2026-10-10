from django.db import migrations


def backfill_operational_progress(apps, schema_editor):
    ProjectGroup = apps.get_model("projects", "ProjectGroup")
    AcObject = apps.get_model("projects", "AcObject")
    MbgDailyReport = apps.get_model("mbg_reports", "MbgDailyReport")
    TeamReport = apps.get_model("internal_time", "TeamReport")

    reported_site_ids = MbgDailyReport.objects.values_list("site_id", flat=True).distinct()
    AcObject.objects.filter(pk__in=reported_site_ids, status="not_started").update(status="started")

    for group in ProjectGroup.objects.iterator():
        active_statuses = list(
            AcObject.objects.filter(group_id=group.pk, is_active=True).values_list("status", flat=True)
        )
        if active_statuses and all(status == "completed" for status in active_statuses):
            ac_status = "completed"
        elif any(status in {"started", "completed"} for status in active_statuses):
            ac_status = "started"
        elif TeamReport.objects.filter(project_group_id=group.pk, direction="ac").exists():
            ac_status = "started"
        else:
            ac_status = "not_started"
        updates = {}
        if group.ac_status != ac_status:
            updates["ac_status"] = ac_status
        if group.dc_status == "not_started" and TeamReport.objects.filter(
            project_group_id=group.pk, direction="dc"
        ).exists():
            updates["dc_status"] = "started"
        if updates:
            ProjectGroup.objects.filter(pk=group.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0005_acobject_status"),
        ("mbg_reports", "0004_performanceexport"),
        ("internal_time", "0003_teamreport_submission_key"),
    ]

    operations = [migrations.RunPython(backfill_operational_progress, migrations.RunPython.noop)]
